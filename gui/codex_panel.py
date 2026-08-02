#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuringClaw Codex Panel — 编程模式面板 (M2)
支持两种模式：
- direct: 复用 ProviderBridge 调云端 Chat Completions
- codex:  通过 subprocess 调 `codex exec`
"""
import os
import shutil
import sys
import json
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, List
from tkinter import Frame, Label, Text, Entry, Button, StringVar, END
from tkinter import ttk

# 4 个 Codex profile，与 ~/.codex/*.config.toml 对应
PROFILES = [
    ("minimax",       "MiniMax (MiniMax-M3)"),
    ("kimi",          "Kimi (kimi-k2.6)"),
    ("deepseek",      "DeepSeek (deepseek-chat)"),
    ("test-provider", "Test Provider"),
]

# profile -> OPENAI_BASE_URL 映射（仅 codex 模式用）
PROFILE_API_BASES: Dict[str, str] = {
    "minimax":       "https://api.minimax.chat/v1",
    "kimi":          "https://api.moonshot.cn/v1",
    "deepseek":      "https://api.deepseek.com/v1",
    "test-provider": "https://api.openai.com/v1",
}

# System prompt 注入：让 AI 输出 Markdown 代码块
CODE_SYSTEM_PROMPT = (
    "你是一个编程助手。请用 Markdown 代码块输出代码，"
    "代码块用 ```python 标注语言。\n\n"
)


class CodexPanel(Frame):
    """编程模式面板：双 Tab 的第二个 Tab"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=app.C["bg"])
        self.app = app
        self.api_keys: Dict[str, str] = {}
        self.runner = None  # CodexRunner 实例（codex 模式时存在）
        self._in_code_block = False
        self._code_buffer: List[str] = []

        self._load_api_keys()
        self._build_ui()

    # ============================================================
    # UI 构建
    # ============================================================
    def _build_ui(self):
        C = self.app.C

        # 顶部控件栏
        top = Frame(self, bg=C["bg"])
        top.pack(fill="x", padx=10, pady=8)

        Label(top, text="Profile:", font=("Consolas", 10, "bold"),
              bg=C["bg"], fg=C["fg"]).pack(side="left")
        self.profile_var = StringVar(value=PROFILES[0][0])
        self.profile_cb = ttk.Combobox(
            top, textvariable=self.profile_var,
            values=[p[0] for p in PROFILES], state="readonly", width=14,
            font=("Consolas", 10)
        )
        self.profile_cb.pack(side="left", padx=6)

        Label(top, text="  模式:", font=("Consolas", 10, "bold"),
              bg=C["bg"], fg=C["fg"]).pack(side="left", padx=(20, 4))
        self.mode_var = StringVar(value="direct")
        for txt, val in [("直接 API", "direct"), ("Codex CLI", "codex")]:
            ttk.Radiobutton(top, text=txt, variable=self.mode_var, value=val).pack(side="left", padx=4)

        # 消息区（流式+高亮）
        mf = Frame(self, bg=C["bg"])
        mf.pack(fill="both", expand=True, padx=10, pady=4)
        mf.grid_rowconfigure(0, weight=1)
        mf.grid_columnconfigure(0, weight=1)
        self.msg_area = Text(
            mf, wrap="word", font=("Consolas", 10),
            bg=C["bgl"], fg=C["fg"], insertbackground=C["fg"],
            bd=0, padx=12, pady=12, state="disabled"
        )
        self.msg_area.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(mf, command=self.msg_area.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.msg_area.config(yscrollcommand=sb.set)

        # 配置高亮 tag（M2-4 实现高亮时也会用）
        self.msg_area.tag_configure("code_kw", foreground="#569cd6")  # 关键字 - 蓝
        self.msg_area.tag_configure("code_str", foreground="#ce9178")  # 字符串 - 橙
        self.msg_area.tag_configure("code_com", foreground="#6a9955")  # 注释 - 绿
        self.msg_area.tag_configure("user_msg", foreground=C["cyan"])
        self.msg_area.tag_configure("ai_msg", foreground=C["fg"])
        self.msg_area.tag_configure("err_msg", foreground=C["red"])
        self.msg_area.tag_configure("info_msg", foreground=C["dim"])

        # 输入区
        bottom = Frame(self, bg=C["bg"])
        bottom.pack(fill="x", padx=10, pady=8)

        self.input_box = Text(
            bottom, height=3, font=("Consolas", 11),
            bg="#2a2a3c", fg=C["fg"], insertbackground=C["cyan"],
            bd=0, padx=10, pady=8
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_frame = Frame(bottom, bg=C["bg"])
        btn_frame.pack(side="right")
        self.send_btn = Button(
            btn_frame, text="发送", font=("Consolas", 11, "bold"),
            bg=C["cyan"], fg="#1e1e2e", bd=0, relief="flat",
            padx=16, pady=6, cursor="hand2", command=self._on_send
        )
        self.send_btn.pack(fill="x", pady=(0, 3))
        self.stop_btn = Button(
            btn_frame, text="停止", font=("Consolas", 11, "bold"),
            bg="#e74c3c", fg="white", bd=0, relief="flat",
            padx=16, pady=6, cursor="hand2", command=self._on_stop, state="disabled"
        )
        self.stop_btn.pack(fill="x")

        # 初始消息
        self._append_system("编程模式就绪。\n- 直接 API: 复用 M1 ProviderBridge\n- Codex CLI: 调 `codex exec` subprocess\n")

    # ============================================================
    # API Key 加载
    # ============================================================
    def _load_api_keys(self):
        key_path = Path.home() / ".TuringClaw" / "api_keys.json"
        if key_path.exists():
            try:
                self.api_keys = json.loads(key_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[WARN] 加载 api_keys.json 失败: {e}")
                self.api_keys = {}
        else:
            self.api_keys = {}

    # ============================================================
    # 消息区辅助
    # ============================================================
    def _append_system(self, text: str):
        self.msg_area.config(state="normal")
        self.msg_area.insert(END, text + "\n", "info_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    def _append_user(self, text: str):
        self.msg_area.config(state="normal")
        self.msg_area.insert(END, "👤 " + text + "\n\n", "user_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    def _append_ai_prefix(self, prefix: str = "🤖 "):
        self.msg_area.config(state="normal")
        self.msg_area.insert(END, prefix, "ai_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    def _append_chunk(self, text: str):
        """实时追加 chunk (M2-4: Markdown 代码块检测 + Python 语法高亮)"""
        from gui.codex_highlight import (
            is_code_block_start,
            is_code_block_end,
            get_code_language,
            is_python_code,
            highlight_python,
        )

        self.msg_area.config(state="normal")
        for line in text.split("\n"):
            if self._in_code_block:
                if is_code_block_end(line):
                    # 代码块结束 - 刷高亮
                    code = "\n".join(self._code_buffer)
                    if code.strip() and is_python_code(code):
                        highlight_python(
                            self.msg_area, code, tag_prefix="py"
                        )
                    else:
                        # 非 Python 原样输出
                        for cl in self._code_buffer:
                            self.msg_area.insert(END, cl + "\n", "ai_msg")
                    self._code_buffer = []
                    self._in_code_block = False
                    self.msg_area.insert(END, line + "\n", "ai_msg")
                else:
                    # 代码块内 - 暂存不插入
                    self._code_buffer.append(line)
            else:
                if is_code_block_start(line):
                    # 代码块开始
                    lang = get_code_language(line)
                    self._in_code_block = True
                    self._code_buffer = []
                    # 显示 ``` 标记 (带语言提示颜色)
                    self.msg_area.insert(END, line + "\n", "ai_msg")
                else:
                    # 普通文本
                    self.msg_area.insert(END, line + "\n", "ai_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    def _append_err(self, text: str):
        self.msg_area.config(state="normal")
        self.msg_area.insert(END, "\n[error] " + text + "\n", "err_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    def _append_info(self, text: str):
        self.msg_area.config(state="normal")
        self.msg_area.insert(END, "\n" + text + "\n", "info_msg")
        self.msg_area.see(END)
        self.msg_area.config(state="disabled")

    # ============================================================
    # 发送 / 停止
    # ============================================================
    def _on_send(self):
        prompt = self.input_box.get("1.0", END).strip()
        if not prompt:
            return
        profile = self.profile_var.get()
        mode = self.mode_var.get()

        self._append_user(f"[{mode}:{profile}] {prompt}")
        self.input_box.delete("1.0", END)
        self.send_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        if mode == "direct":
            self._run_direct_api(profile, prompt)
        else:
            self._run_codex_cli(profile, prompt)

    def _on_stop(self):
        """停止当前请求（API 模式或 CLI 模式）"""
        if self.mode_var.get() == "codex" and self.runner:
            self.runner.stop()
        # 直接 API 模式目前无 cancel 接口（M1 没实现），仅重置 UI
        self._append_info("[已停止]")
        self.send_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _on_complete(self):
        """请求结束（成功/失败都调用）"""
        self.send_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    # ============================================================
    # 直接 API 模式（M2-2）
    # ============================================================
    def _run_direct_api(self, profile: str, prompt: str):
        """复用 ProviderBridge（来自 M1）。先 update_config 切到目标 profile，再 stream_chat。"""
        # 找匹配的 ProviderInfo
        provider = None
        try:
            from gui.providers import FREE_PROVIDERS
            for p in FREE_PROVIDERS.values():
                if p.name == profile:
                    provider = p
                    break
        except ImportError:
            self._append_err("无法加载 ProviderInfo")
            self._on_complete()
            return

        if not provider:
            self._append_err(f"未知 profile: {profile}")
            self._on_complete()
            return

        if not self.app.bridge:
            self._append_err("ProviderBridge 不可用，请检查 M1 集成")
            self._on_complete()
            return

        # 解析 API Key (优先用 panel 自己加载的 api_keys.json)
        api_key = self.api_keys.get(profile, "")
        if not api_key:
            self._append_err(f"未配置 {profile} 的 API Key（请检查 ~/.TuringClaw/api_keys.json）")
            self._on_complete()
            return

        # 切到目标 provider
        api_base = provider.api_base_url or ""
        try:
            self.app.bridge.update_config(api_key=api_key, api_base=api_base)
        except Exception as e:
            self._append_err(f"update_config 失败: {e}")
            self._on_complete()
            return

        # 注入 system prompt 引导 Markdown 输出
        full_prompt = CODE_SYSTEM_PROMPT + prompt
        self._append_ai_prefix()

        # 记录 prompt 用量
        self._prompt_chars = len(full_prompt)

        try:
            self.app.bridge.stream_chat(
                messages=[{"role": "user", "content": full_prompt}],
                model=provider.default_model or None,
                on_chunk=lambda text: self.after(0, lambda: self._append_chunk(text)),
                on_complete=lambda usage: self.after(0, lambda: self._on_direct_complete(usage)),
                on_error=lambda err: self.after(0, lambda: self._on_direct_error(err)),
            )
        except Exception as e:
            self._append_err(f"stream_chat 启动失败: {e}")
            self._on_complete()

    def _on_direct_complete(self, usage):
        # Minimax 等 provider 不返回 usage，需 fallback 估算
        in_tokens = (usage or {}).get("prompt_tokens", 0) or 0
        out_tokens = (usage or {}).get("completion_tokens", 0) or 0
        if not in_tokens and not out_tokens:
            # 估算：英文 1 token ≈ 4 chars；中文 1 token ≈ 1.5 chars
            # 出于简化一律用 1 token ≈ 3 chars
            prompt_chars = getattr(self, "_prompt_chars", 0)
            content = self.msg_area.get("1.0", "end")
            in_tokens = prompt_chars // 3 if prompt_chars else 0
            out_tokens = max(1, len(content) // 30)  # 粗略估计
            self._append_info(
                f"[Token 估算] in={in_tokens} out={out_tokens} (API 未返回 usage)"
            )
        else:
            self._append_info(
                f"[Token: in={in_tokens} out={out_tokens}]"
            )
        self._on_complete()

    def _on_direct_error(self, err):
        self._append_err(str(err)[:200])
        self._on_complete()

    # ============================================================
    # Codex CLI 模式（M2-3）
    # ============================================================
    def _run_codex_cli(self, profile: str, prompt: str):
        """通过 subprocess 调 codex exec"""
        self._append_ai_prefix()
        # CodexRunner 内嵌在本文件（避免 codex_runner.py 单独维护）
        from gui.codex_panel import CodexRunner

        self.runner = CodexRunner(
            api_keys=self.api_keys,
            on_chunk=lambda text: self.after(0, lambda: self._append_chunk(text)),
            on_done=lambda code=None: self.after(0, lambda: self._on_codex_done(code)),
            on_error=lambda err: self.after(0, lambda: self._append_err(err)),
        )
        self.runner.run(profile, prompt)

    def _on_codex_done(self, returncode):
        if returncode is not None and returncode != 0:
            self._append_info(f"[codex exit code: {returncode}]")
        else:
            self._append_info("[codex 完成]")
        self._on_complete()


# ============================================================
# CodexRunner — subprocess 封装（M2-3）
# ============================================================
class CodexRunner:
    """管理 `codex exec` subprocess 的生命周期"""

    def __init__(
        self,
        api_keys: Dict[str, str],
        on_chunk: Callable[[str], None],
        on_done: Callable[[Optional[int]], None],
        on_error: Callable[[str], None],
    ):
        self.api_keys = api_keys
        self.on_chunk = on_chunk
        self.on_done = on_done
        self.on_error = on_error
        self.proc: Optional[subprocess.Popen] = None
        self._stopped = False

    def _build_cmd(self, profile: str, prompt: str) -> list:
        """构造 codex CLI 命令。Windows 下用 .cmd 包装，避开 sh 脚本路径解析。

        背景：codex 在 npm-global 是 sh 脚本（#!/bin/sh），Python subprocess 直接调
        走 PATH 会 FileNotFoundError。codex.cmd 是 Windows 入口，PATH 中可解析。

        策略：Windows 下始终优先 codex.cmd，避免 shutil.which('codex') 误报导致
        返回裸 'codex' 然后 Popen FileNotFoundError。
        """
        if os.name == 'nt':
            # Windows: 始终优先 codex.cmd（避免裸 'codex' 走 sh 脚本路径）
            if shutil.which('codex.cmd'):
                return ['codex.cmd', 'exec', '-p', profile, '--skip-git-repo-check', prompt]
            # 兜底：全路径（QClaw npm-global 优先于系统 npm）
            for base in [r'C:\\Users\\Administrator\\AppData\\Roaming\\QClaw\\npm-global',
                         os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm')]:
                candidate = os.path.join(base, 'codex.cmd')
                if os.path.exists(candidate):
                    return [candidate, 'exec', '-p', profile, '--skip-git-repo-check', prompt]
        # 非 Windows 或兜底失败
        return ['codex', 'exec', '-p', profile, '--skip-git-repo-check', prompt]

    def run(self, profile: str, prompt: str, cwd: Optional[str] = None) -> None:
        """启动 codex exec subprocess"""
        api_key = self.api_keys.get(profile, "")
        if not api_key:
            self.on_error(f"未配置 {profile} 的 API Key")
            return

        env = os.environ.copy()
        env["OPENAI_API_KEY"] = api_key
        env["OPENAI_BASE_URL"] = PROFILE_API_BASES.get(profile, "")

        # Windows: 用 .cmd 包装，避免裸 'codex' 走 sh 脚本路径
        cmd = self._build_cmd(profile, prompt)

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=cwd or os.getcwd(),
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            self.on_error("找不到 codex 命令。请先安装 Codex CLI: npm i -g @openai/codex")
            return
        except Exception as e:
            self.on_error(f"启动 Codex 失败: {e}")
            return

        threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self) -> None:
        """读 subprocess stdout"""
        try:
            assert self.proc and self.proc.stdout
            for line in iter(self.proc.stdout.readline, ""):
                if self._stopped:
                    break
                # 过滤 Codex 内部日志
                if line.startswith("[DEBUG]") or line.startswith("[INFO]"):
                    continue
                if line.strip():
                    self.on_chunk(line)
        except Exception as e:
            self.on_error(f"读取输出失败: {e}")
        finally:
            if self.proc:
                self.proc.wait()
            self.on_done(self.proc.returncode if self.proc else None)

    def stop(self) -> None:
        """终止 subprocess（terminate + taskkill 兜底）"""
        self._stopped = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Windows 强制 kill
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                        capture_output=True, timeout=5
                    )
                except Exception as e:
                    self.on_error(f"强制终止失败: {e}")
