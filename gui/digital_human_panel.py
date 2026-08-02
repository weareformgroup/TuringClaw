#!/usr/bin/env python3
"""
M7: Digital Human Panel — Tkinter GUI Tab for EchoMimicV3
===========================================================
Adds a "🎭 数字人" tab to TuringClaw's notebook.

Features:
  - Image upload (reference portrait)
  - Audio upload or TTS text input
  - Inference parameter controls (steps, CFG, resolution, seed)
  - Progress log display
  - Output video preview

Layout:
  ┌─────────────────────────────────────────────┐
  │ [Image Preview]  │  [Audio Info / TTS]      │
  │                  │                          │
  ├──────────────────┴──────────────────────────┤
  │ Parameters: steps | CFG | resolution | seed │
  ├─────────────────────────────────────────────┤
  │ [Generate Video]  [Open Output]             │
  ├─────────────────────────────────────────────┤
  │ Progress Log:                                │
  │ ┌─────────────────────────────────────────┐ │
  │ │ [inference output lines...]              │ │
  │ └─────────────────────────────────────────┘ │
  └─────────────────────────────────────────────┘
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import digital human engine
try:
    from gui.digital_human import EchoMimicEngine, TTSEngine
    ENGINE_AVAILABLE = True
except ImportError:
    try:
        from digital_human import EchoMimicEngine, TTSEngine
        ENGINE_AVAILABLE = True
    except ImportError:
        ENGINE_AVAILABLE = False


class DigitalHumanPanel(ttk.Frame):
    """Digital Human Tab for TuringClaw GUI."""

    def __init__(self, parent, main_app=None):
        super().__init__(parent)
        self.parent = parent
        self.main_app = main_app

        # Theme colors (match TuringClaw's theme)
        self.C = getattr(main_app, "C", {
            "bg": "#1e1e2e",
            "bgl": "#181825",
            "fg": "#cdd6f4",
            "cyan": "#89dceb",
            "green": "#a6e3a1",
            "red": "#f38ba8",
            "yellow": "#f9e2af",
        })

        # Engine
        self.engine = EchoMimicEngine() if ENGINE_AVAILABLE else None
        self.tts = TTSEngine() if ENGINE_AVAILABLE else None

        # State
        self.image_path = None
        self.audio_path = None
        self.output_path = None
        self.is_generating = False
        self.generate_thread = None

        # Demo data path
        self.demo_dir = os.path.join(
            os.environ.get("ECHOMIMIC_ROOT", r"C:\Users\Administrator\echomimic_v3"),
            "datasets", "echomimicv3_demos"
        )

        self._build_ui()
        self._update_status()

    def _build_ui(self):
        """Build the panel UI."""
        self.configure(style="Dark.TFrame")

        # Main container
        main_frame = tk.Frame(self, bg=self.C["bg"])
        main_frame.pack(fill="both", expand=True, padx=14, pady=10)

        # ─── Title ───
        title_label = tk.Label(
            main_frame,
            text="🎭 数字人 — EchoMimicV3",
            font=("Consolas", 14, "bold"),
            bg=self.C["bg"],
            fg=self.C["cyan"],
        )
        title_label.pack(anchor="w", pady=(0, 8))

        # ─── Status bar ───
        self.status_label = tk.Label(
            main_frame,
            text="Checking engine status...",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["yellow"],
            anchor="w",
            padx=8,
            pady=4,
        )
        self.status_label.pack(fill="x", pady=(0, 8))

        # ─── Input section ───
        input_frame = tk.Frame(main_frame, bg=self.C["bg"])
        input_frame.pack(fill="x", pady=(0, 8))

        # Image selection
        img_frame = tk.LabelFrame(
            input_frame,
            text="Reference Image",
            font=("Consolas", 10),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=1,
            relief="solid",
        )
        img_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.img_label = tk.Label(
            img_frame,
            text="No image selected",
            font=("Consolas", 9),
            bg=self.C["bg"],
            fg=self.C["fg"],
            width=30,
            height=6,
            relief="sunken",
            bd=1,
        )
        self.img_label.pack(padx=8, pady=8, fill="both", expand=True)

        btn_frame_img = tk.Frame(img_frame, bg=self.C["bgl"])
        btn_frame_img.pack(fill="x", padx=8, pady=(0, 8))

        tk.Button(
            btn_frame_img,
            text="Browse",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=0,
            padx=10,
            cursor="hand2",
            command=self._browse_image,
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            btn_frame_img,
            text="Demo",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=0,
            padx=10,
            cursor="hand2",
            command=self._load_demo_image,
        ).pack(side="left")

        # Audio selection
        audio_frame = tk.LabelFrame(
            input_frame,
            text="Audio Input",
            font=("Consolas", 10),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=1,
            relief="solid",
        )
        audio_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.audio_label = tk.Label(
            audio_frame,
            text="No audio selected",
            font=("Consolas", 9),
            bg=self.C["bg"],
            fg=self.C["fg"],
            width=30,
            height=3,
            relief="sunken",
            bd=1,
        )
        self.audio_label.pack(padx=8, pady=8, fill="x")

        # TTS input
        tts_frame = tk.Frame(audio_frame, bg=self.C["bgl"])
        tts_frame.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(
            tts_frame,
            text="TTS:",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
        ).pack(side="left")

        self.tts_entry = tk.Entry(
            tts_frame,
            font=("Consolas", 9),
            bg=self.C["bg"],
            fg=self.C["fg"],
            relief="flat",
            bd=1,
        )
        self.tts_entry.pack(side="left", fill="x", expand=True, padx=4)

        tk.Button(
            tts_frame,
            text="Synth",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["cyan"],
            bd=0,
            padx=8,
            cursor="hand2",
            command=self._tts_synthesize,
        ).pack(side="left")

        btn_frame_audio = tk.Frame(audio_frame, bg=self.C["bgl"])
        btn_frame_audio.pack(fill="x", padx=8, pady=(0, 8))

        tk.Button(
            btn_frame_audio,
            text="Browse",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=0,
            padx=10,
            cursor="hand2",
            command=self._browse_audio,
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            btn_frame_audio,
            text="Demo",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=0,
            padx=10,
            cursor="hand2",
            command=self._load_demo_audio,
        ).pack(side="left")

        # ─── Parameters ───
        param_frame = tk.LabelFrame(
            main_frame,
            text="Inference Parameters",
            font=("Consolas", 10),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=1,
            relief="solid",
        )
        param_frame.pack(fill="x", pady=(0, 8))

        params_inner = tk.Frame(param_frame, bg=self.C["bgl"])
        params_inner.pack(fill="x", padx=8, pady=8)

        # Steps
        tk.Label(params_inner, text="Steps:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=0, column=0, padx=4, pady=4, sticky="e")
        self.steps_var = tk.IntVar(value=8)
        tk.Spinbox(params_inner, from_=5, to=50, textvariable=self.steps_var,
                   width=5, font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                   relief="flat").grid(row=0, column=1, padx=4, pady=4)

        # Guidance Scale
        tk.Label(params_inner, text="Text CFG:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=0, column=2, padx=4, pady=4, sticky="e")
        self.cfg_var = tk.DoubleVar(value=6.0)
        tk.Spinbox(params_inner, from_=1.0, to=15.0, increment=0.5,
                   textvariable=self.cfg_var, width=5, font=("Consolas", 9),
                   bg=self.C["bg"], fg=self.C["fg"], relief="flat").grid(row=0, column=3, padx=4, pady=4)

        # Audio CFG
        tk.Label(params_inner, text="Audio CFG:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=0, column=4, padx=4, pady=4, sticky="e")
        self.audio_cfg_var = tk.DoubleVar(value=3.0)
        tk.Spinbox(params_inner, from_=0.5, to=10.0, increment=0.5,
                   textvariable=self.audio_cfg_var, width=5, font=("Consolas", 9),
                   bg=self.C["bg"], fg=self.C["fg"], relief="flat").grid(row=0, column=5, padx=4, pady=4)

        # Resolution
        tk.Label(params_inner, text="Resolution:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=1, column=0, padx=4, pady=4, sticky="e")
        self.res_var = tk.StringVar(value="768x768")
        res_combo = ttk.Combobox(params_inner, textvariable=self.res_var,
                                  values=["512x512", "768x768"], width=8,
                                  font=("Consolas", 9), state="readonly")
        res_combo.grid(row=1, column=1, padx=4, pady=4)

        # Video Length
        tk.Label(params_inner, text="Frames:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=1, column=2, padx=4, pady=4, sticky="e")
        self.frames_var = tk.IntVar(value=81)
        tk.Spinbox(params_inner, from_=17, to=201, textvariable=self.frames_var,
                   width=5, font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                   relief="flat").grid(row=1, column=3, padx=4, pady=4)

        # Seed
        tk.Label(params_inner, text="Seed:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=1, column=4, padx=4, pady=4, sticky="e")
        self.seed_var = tk.IntVar(value=43)
        tk.Spinbox(params_inner, from_=0, to=99999, textvariable=self.seed_var,
                   width=5, font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                   relief="flat").grid(row=1, column=5, padx=4, pady=4)

        # Prompt
        tk.Label(params_inner, text="Prompt:", font=("Consolas", 9),
                 bg=self.C["bgl"], fg=self.C["fg"]).grid(row=2, column=0, padx=4, pady=4, sticky="ne")
        self.prompt_var = tk.StringVar(value="A person is speaking.")
        tk.Entry(params_inner, textvariable=self.prompt_var,
                 font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                 relief="flat", bd=1, width=40).grid(row=2, column=1, columnspan=5, padx=4, pady=4, sticky="we")

        # ─── Action buttons ───
        action_frame = tk.Frame(main_frame, bg=self.C["bg"])
        action_frame.pack(fill="x", pady=(0, 8))

        self.generate_btn = tk.Button(
            action_frame,
            text="🎬 Generate Video",
            font=("Consolas", 11, "bold"),
            bg=self.C["cyan"],
            fg=self.C["bg"],
            bd=0,
            padx=20,
            pady=6,
            cursor="hand2",
            command=self._on_generate,
        )
        self.generate_btn.pack(side="left")

        tk.Button(
            action_frame,
            text="📂 Open Output",
            font=("Consolas", 9),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=0,
            padx=12,
            cursor="hand2",
            command=self._open_output,
        ).pack(side="left", padx=(8, 0))

        # ─── Progress log ───
        log_frame = tk.LabelFrame(
            main_frame,
            text="Progress Log",
            font=("Consolas", 10),
            bg=self.C["bgl"],
            fg=self.C["fg"],
            bd=1,
            relief="solid",
        )
        log_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 9),
            bg=self.C["bg"],
            fg=self.C["fg"],
            relief="flat",
            bd=0,
            height=8,
            wrap="word",
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scroll.set)

    def _log(self, message):
        """Append a message to the progress log."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _update_status(self):
        """Update engine status display."""
        if not ENGINE_AVAILABLE:
            self.status_label.config(
                text="❌ Engine module not available",
                fg=self.C["red"],
            )
            return

        status = self.engine.get_status()
        ready = self.engine.is_ready()

        if ready:
            self.status_label.config(
                text="✅ Engine ready — all weights loaded",
                fg=self.C["green"],
            )
        else:
            ready_count = sum([
                status["transformer_ready"],
                status["wan_model_ready"],
                status["wav2vec_ready"],
            ])
            self.status_label.config(
                text=f"⚠️ Engine partial ({ready_count}/3 models ready) — "
                     + "; ".join(status["issues"][:2]),
                fg=self.C["yellow"],
            )

    # ─── Image handling ───

    def _browse_image(self):
        path = filedialog.askopenfilename(
            title="Select Reference Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All", "*.*")],
        )
        if path:
            self.image_path = path
            self.img_label.config(text=Path(path).name)
            self._log(f"Image selected: {path}")

    def _load_demo_image(self):
        img_dir = os.path.join(self.demo_dir, "imgs")
        if not os.path.isdir(img_dir):
            self._log(f"Demo directory not found: {img_dir}")
            return

        files = [f for f in os.listdir(img_dir) if f.endswith((".png", ".jpg", ".jpeg"))]
        if not files:
            self._log("No demo images found")
            return

        path = os.path.join(img_dir, files[0])
        self.image_path = path
        self.img_label.config(text=files[0])
        self._log(f"Demo image loaded: {files[0]}")

    # ─── Audio handling ───

    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.ogg"), ("All", "*.*")],
        )
        if path:
            self.audio_path = path
            self.audio_label.config(text=Path(path).name)
            self._log(f"Audio selected: {path}")

    def _load_demo_audio(self):
        audio_dir = os.path.join(self.demo_dir, "audios")
        if not os.path.isdir(audio_dir):
            self._log(f"Demo directory not found: {audio_dir}")
            return

        files = [f for f in os.listdir(audio_dir) if f.endswith((".wav", ".mp3"))]
        if not files:
            self._log("No demo audio files found")
            return

        path = os.path.join(audio_dir, files[0])
        self.audio_path = path
        self.audio_label.config(text=files[0])
        self._log(f"Demo audio loaded: {files[0]}")

    def _tts_synthesize(self):
        """Synthesize TTS audio from text input."""
        text = self.tts_entry.get().strip()
        if not text:
            self._log("TTS text is empty")
            return

        if not self.tts or not self.tts.is_available():
            self._log("TTS not available (install edge-tts: pip install edge-tts)")
            return

        self._log(f"Synthesizing TTS: {text[:50]}...")
        result = self.tts.synthesize(text)

        if result["success"]:
            self.audio_path = result["audio_path"]
            self.audio_label.config(text=f"TTS: {Path(result['audio_path']).name}")
            self._log(f"TTS audio saved: {result['audio_path']}")
        else:
            self._log(f"TTS error: {result['error']}")

    # ─── Generate ───

    def _on_generate(self):
        if self.is_generating:
            self._log("Already generating, please wait...")
            return

        if not self.image_path:
            messagebox.showwarning("Missing Input", "Please select a reference image")
            return

        if not self.audio_path:
            messagebox.showwarning("Missing Input", "Please select an audio file or use TTS")
            return

        if not ENGINE_AVAILABLE or not self.engine.is_ready():
            messagebox.showerror("Engine Not Ready", "EchoMimic engine is not ready. Check model weights.")
            return

        # Parse resolution
        try:
            w, h = self.res_var.get().split("x")
            sample_size = (int(h), int(w))
        except Exception:
            sample_size = (768, 768)

        # Start generation
        self.is_generating = True
        self.generate_btn.config(state="disabled", text="⏳ Generating...")
        self._log("=" * 50)
        self._log(f"Starting generation...")
        self._log(f"  Image: {self.image_path}")
        self._log(f"  Audio: {self.audio_path}")
        self._log(f"  Steps: {self.steps_var.get()}")
        self._log(f"  Text CFG: {self.cfg_var.get()}")
        self._log(f"  Audio CFG: {self.audio_cfg_var.get()}")
        self._log(f"  Resolution: {self.res_var.get()}")
        self._log(f"  Frames: {self.frames_var.get()}")
        self._log(f"  Seed: {self.seed_var.get()}")

        def progress_cb(line):
            # Thread-safe log update
            self.after(0, lambda: self._log(line))

        def result_cb(result):
            # Thread-safe result handling
            self.after(0, lambda: self._on_generate_done(result))

        self.generate_thread, _ = self.engine.generate_video_async(
            image_path=self.image_path,
            audio_path=self.audio_path,
            prompt=self.prompt_var.get(),
            video_length=self.frames_var.get(),
            num_inference_steps=self.steps_var.get(),
            guidance_scale=self.cfg_var.get(),
            audio_guidance_scale=self.audio_cfg_var.get(),
            sample_size=sample_size,
            seed=self.seed_var.get(),
            progress_callback=progress_cb,
            result_callback=result_cb,
        )

    def _on_generate_done(self, result):
        """Called when generation completes."""
        self.is_generating = False
        self.generate_btn.config(state="normal", text="🎬 Generate Video")

        if result["success"]:
            self.output_path = result["output_path"]
            self._log(f"\n✅ Video generated: {self.output_path}")
            # Offer to open
            if messagebox.askyesno("Success", f"Video generated!\n\n{self.output_path}\n\nOpen now?"):
                self._open_output()
        else:
            self._log(f"\n❌ Generation failed: {result['error']}")
            messagebox.showerror("Generation Failed", result["error"])

    def _open_output(self):
        """Open output directory."""
        output_dir = os.path.join(
            os.environ.get("ECHOMIMIC_ROOT", r"C:\Users\Administrator\echomimic_v3"),
            "outputs"
        )
        if self.output_path and os.path.isfile(self.output_path):
            os.startfile(self.output_path)
        elif os.path.isdir(output_dir):
            os.startfile(output_dir)
        else:
            self._log("No output directory found")


__all__ = ["DigitalHumanPanel"]
