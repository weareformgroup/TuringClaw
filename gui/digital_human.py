#!/usr/bin/env python3
"""
M7: Digital Human Module — EchoMimicV3 Integration
====================================================
Wraps EchoMimicV3-Flash-Pro inference pipeline for TuringClaw GUI.

Architecture:
  1. EchoMimicEngine — core inference wrapper (subprocess call to echomimic_v3 env)
  2. TTSEngine — text-to-speech for text-driven avatar animation
  3. DigitalHumanPanel — Tkinter GUI tab

Key Constraints:
  - RTX 3050 4GB VRAM: use sequential_cpu_offload, bfloat16, 8 steps
  - EchoMimicV3 env is separate conda env (echomimic_v3)
  - Inference runs as subprocess to isolate CUDA memory
"""

import os
import sys
import json
import subprocess
import threading
import tempfile
import time
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

# EchoMimic V3 project root
ECHOMIMIC_ROOT = os.environ.get(
    "ECHOMIMIC_ROOT",
    r"C:\Users\Administrator\echomimic_v3"
)

# Conda environment for EchoMimic
ECHOMIMIC_CONDA_ENV = os.environ.get(
    "ECHOMIMIC_CONDA_ENV",
    r"C:\Users\Administrator\anaconda3\envs\echomimic_v3"
)

# Weights root
WEIGHTS_ROOT = os.path.join(ECHOMIMIC_ROOT, "weights", "flash-pro")

# Model paths
WAN_MODEL_DIR = os.path.join(WEIGHTS_ROOT, "Wan2.1-Fun-V1.1-1.3B-InP")
TRANSFORMER_PATH = os.path.join(WEIGHTS_ROOT, "transformer", "diffusion_pytorch_model.safetensors")
WAV2VEC_DIR = os.path.join(WEIGHTS_ROOT, "chinese-wav2vec2-base")
CONFIG_PATH = os.path.join(ECHOMIMIC_ROOT, "config", "config.yaml")

# Output directory
OUTPUT_DIR = os.path.join(ECHOMIMIC_ROOT, "outputs")

# Python executable for echomimic env
ECHOMIMIC_PYTHON = os.path.join(ECHOMIMIC_CONDA_ENV, "python.exe")

# Inference script
INFER_SCRIPT = os.path.join(ECHOMIMIC_ROOT, "infer_flash.py")


# ─── EchoMimicEngine ─────────────────────────────────────────────────────────

class EchoMimicEngine:
    """
    EchoMimicV3-Flash-Pro inference engine.
    
    Runs inference as a subprocess in the echomimic_v3 conda environment
    to isolate CUDA memory and dependencies.
    """

    def __init__(self):
        self._check_paths()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _check_paths(self):
        """Verify all required files exist."""
        issues = []
        if not os.path.isfile(INFER_SCRIPT):
            issues.append(f"Infer script not found: {INFER_SCRIPT}")
        if not os.path.isfile(CONFIG_PATH):
            issues.append(f"Config not found: {CONFIG_PATH}")
        if not os.path.isfile(TRANSFORMER_PATH):
            issues.append(f"Transformer weights not found: {TRANSFORMER_PATH}")
        if not os.path.isfile(ECHOMIMIC_PYTHON):
            issues.append(f"Python not found: {ECHOMIMIC_PYTHON}")
        # Wan model dir should have subdirectories
        if os.path.isdir(WAN_MODEL_DIR):
            subdirs = os.listdir(WAN_MODEL_DIR)
            if len(subdirs) < 3:
                issues.append(f"Wan model dir seems incomplete: {WAN_MODEL_DIR} ({len(subdirs)} items)")
        else:
            issues.append(f"Wan model dir not found: {WAN_MODEL_DIR}")
        self._issues = issues

    def get_status(self):
        """Return engine status dict."""
        return {
            "echomimic_root": ECHOMIMIC_ROOT,
            "conda_env": ECHOMIMIC_CONDA_ENV,
            "weights_root": WEIGHTS_ROOT,
            "transformer_ready": os.path.isfile(TRANSFORMER_PATH),
            "wan_model_ready": os.path.isdir(WAN_MODEL_DIR) and len(os.listdir(WAN_MODEL_DIR)) >= 3,
            "wav2vec_ready": os.path.isdir(WAV2VEC_DIR),
            "issues": self._issues,
        }

    def is_ready(self):
        """Check if engine is ready for inference."""
        return len(self._issues) == 0

    def generate_video(
        self,
        image_path,
        audio_path,
        prompt="A person is speaking.",
        video_length=81,
        num_inference_steps=8,
        guidance_scale=6.0,
        audio_guidance_scale=3.0,
        sample_size=(768, 768),
        seed=43,
        progress_callback=None,
    ):
        """
        Generate a lip-synced video from image + audio.
        
        Args:
            image_path: Path to reference portrait image
            audio_path: Path to audio file (wav/mp3)
            prompt: Text description of the person/scene
            video_length: Number of frames (81 ≈ 3.2s at 25fps)
            num_inference_steps: 8 for flash-pro (fast)
            guidance_scale: Text CFG (3-6 recommended)
            audio_guidance_scale: Audio CFG (1.8-3 recommended)
            sample_size: (height, width) tuple
            seed: Random seed
            progress_callback: callable(line: str) for progress updates
            
        Returns:
            dict: {"success": bool, "output_path": str, "error": str}
        """
        if not self.is_ready():
            return {
                "success": False,
                "output_path": None,
                "error": "Engine not ready: " + "; ".join(self._issues),
            }

        # Build command
        cmd = [
            ECHOMIMIC_PYTHON,
            INFER_SCRIPT,
            "--image_path", image_path,
            "--audio_path", audio_path,
            "--prompt", prompt,
            "--num_inference_steps", str(num_inference_steps),
            "--config_path", CONFIG_PATH,
            "--model_name", WAN_MODEL_DIR,
            "--ckpt_idx", "50000",
            "--transformer_path", TRANSFORMER_PATH,
            "--save_path", OUTPUT_DIR,
            "--wav2vec_model_dir", WAV2VEC_DIR,
            "--sampler_name", "Flow_Unipc",
            "--video_length", str(video_length),
            "--guidance_scale", str(guidance_scale),
            "--audio_guidance_scale", str(audio_guidance_scale),
            "--audio_scale", "1.0",
            "--neg_scale", "1.0",
            "--neg_steps", "0",
            "--seed", str(seed),
            "--enable_teacache",
            "--teacache_threshold", "0.1",
            "--num_skip_start_steps", "5",
            "--enable_riflex",
            "--riflex_k", "6",
            "--ulysses_degree", "1",
            "--ring_degree", "1",
            "--weight_dtype", "bfloat16",
            "--sample_size", str(sample_size[0]), str(sample_size[1]),
            "--fps", "25",
            "--add_prompt", "",
            "--negative_prompt", "",
            "--shift", "5.0",
            "--GPU_memory_mode", "sequential_cpu_offload",
        ]

        try:
            # Run inference as subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ECHOMIMIC_ROOT,
                env=self._build_env(),
            )

            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    output_lines.append(line)
                    if progress_callback:
                        progress_callback(line)

            process.wait()
            retcode = process.returncode

            if retcode != 0:
                return {
                    "success": False,
                    "output_path": None,
                    "error": f"Inference failed (exit code {retcode}):\n" + "\n".join(output_lines[-20:]),
                }

            # Find output video
            image_name = Path(image_path).stem
            expected_output = os.path.join(OUTPUT_DIR, f"{image_name}_output.mp4")

            if os.path.isfile(expected_output):
                return {
                    "success": True,
                    "output_path": expected_output,
                    "error": None,
                }
            else:
                # Search for any recently created mp4
                mp4_files = [
                    os.path.join(OUTPUT_DIR, f)
                    for f in os.listdir(OUTPUT_DIR)
                    if f.endswith(".mp4")
                ]
                if mp4_files:
                    latest = max(mp4_files, key=os.path.getmtime)
                    return {
                        "success": True,
                        "output_path": latest,
                        "error": None,
                    }
                return {
                    "success": False,
                    "output_path": None,
                    "error": "Output video not found after inference",
                }

        except Exception as e:
            return {
                "success": False,
                "output_path": None,
                "error": str(e),
            }

    def _build_env(self):
        """Build environment for subprocess."""
        env = os.environ.copy()
        # Ensure conda env is in PATH
        env["PATH"] = os.path.join(ECHOMIMIC_CONDA_ENV) + os.pathsep + env.get("PATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["CUDA_VISIBLE_DEVICES"] = "0"
        return env

    def generate_video_async(self, *args, **kwargs):
        """
        Async wrapper for generate_video.
        
        Returns: threading.Thread (call .join() to wait)
        Callback: result_callback(result_dict) will be called when done.
        """
        result_holder = {}
        callback = kwargs.pop("progress_callback", None)
        result_callback = kwargs.pop("result_callback", None)

        def _worker():
            result = self.generate_video(*args, progress_callback=callback, **kwargs)
            result_holder["result"] = result
            if result_callback:
                result_callback(result)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread, result_holder


# ─── TTS Engine (placeholder for future integration) ────────────────────────

class TTSEngine:
    """
    Text-to-Speech engine for converting text to audio.
    
    Phase 1: Use edge-tts (free, no API key needed, Microsoft Edge TTS)
    Phase 2: Integrate with TuringClaw's provider bridge for cloud TTS
    """

    def __init__(self):
        self._available = False
        try:
            import edge_tts
            self._available = True
        except ImportError:
            pass

    def is_available(self):
        return self._available

    def synthesize(self, text, voice="zh-CN-XiaoxiaoNeural", output_path=None):
        """
        Convert text to speech audio file.
        
        Args:
            text: Text to synthesize
            voice: Voice name (zh-CN-XiaoxiaoNeural, zh-CN-YunxiNeural, etc.)
            output_path: Output wav file path. If None, creates temp file.
            
        Returns:
            dict: {"success": bool, "audio_path": str, "error": str}
        """
        if not self._available:
            return {"success": False, "audio_path": None, "error": "edge-tts not installed"}

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="tts_")
            os.close(fd)

        try:
            import asyncio
            import edge_tts

            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)
                return output_path

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_synthesize())
            loop.close()

            return {"success": True, "audio_path": result, "error": None}
        except Exception as e:
            return {"success": False, "audio_path": None, "error": str(e)}


# ─── Module Exports ──────────────────────────────────────────────────────────

__all__ = ["EchoMimicEngine", "TTSEngine"]

# ─── Self-Test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("EchoMimicV3 Digital Human Engine — Self Test")
    print("=" * 50)

    engine = EchoMimicEngine()
    status = engine.get_status()

    print(f"EchoMimic Root:    {status['echomimic_root']}")
    print(f"Conda Env:         {status['conda_env']}")
    print(f"Weights Root:      {status['weights_root']}")
    print(f"Transformer Ready: {status['transformer_ready']}")
    print(f"Wan Model Ready:   {status['wan_model_ready']}")
    print(f"Wav2Vec Ready:     {status['wav2vec_ready']}")
    print(f"Engine Ready:      {engine.is_ready()}")

    if status["issues"]:
        print("\nIssues:")
        for issue in status["issues"]:
            print(f"  - {issue}")
    else:
        print("\nAll checks passed!")

    print(f"\nTTS Engine:")
    tts = TTSEngine()
    print(f"  Available: {tts.is_available()}")
