#!/usr/bin/env python3
# TuringClaw GUI - China Telecom AI Assistant
import os, sys, threading, json, io, urllib.request
from pathlib import Path
from gui.chat_history import ChatHistoryManager
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Text, Entry, Frame, Label, Button, Canvas, Scrollbar, StringVar

# Initialize defaults
FREE_PROVIDERS = {}
PROVIDERS_AVAILABLE = False
token_tracker = None

try:
    from gui.providers import FREE_PROVIDERS, get_all_providers_status, TokenTracker, token_tracker
    PROVIDERS_AVAILABLE = True
except ImportError:
    try:
        from providers import FREE_PROVIDERS, get_all_providers_status, TokenTracker, token_tracker
        PROVIDERS_AVAILABLE = True
    except ImportError:
        PROVIDERS_AVAILABLE = False

# Privacy Router - 三级隐私路由
privacy_router = None
privacy_audit_logger = None
try:
    from gui.privacy_router import PrivacyRouter, PrivacyAuditLogger
    privacy_router = PrivacyRouter()
    privacy_audit_logger = PrivacyAuditLogger()
except ImportError:
    try:
        from privacy_router import PrivacyRouter, PrivacyAuditLogger
        privacy_router = PrivacyRouter()
        privacy_audit_logger = PrivacyAuditLogger()
    except ImportError:
        pass
def load_ct_logo():
    try:
        from PIL import Image
        gui_dir = Path(__file__).parent
        for p in [gui_dir / "chinatelecom.jpeg", gui_dir.parent / "gui" / "chinatelecom.jpeg"]:
            if p.exists():
                img = Image.open(str(p)).convert("RGBA").resize((48, 48), Image.LANCZOS)
                r, g, b, a = img.split()
                def shift(c, d):
                    lut = [max(0, min(255, i + d)) for i in range(256)]
                    return c.point(lut)
                logos = {}
                for n, tr, tg, tb in [("green", -60, 90, -90), ("red", 180, -80, -100), ("orange", 140, 30, -120), ("purple", 70, -50, 80)]:
                    img2 = Image.open(str(p)).convert("RGBA").resize((48, 48), Image.LANCZOS)
                    r2, g2, b2, a2 = img2.split()
                    buf2 = io.BytesIO()
                    Image.merge("RGBA", (shift(r2, tr), shift(g2, tg), shift(b2, tb), a2)).save(buf2, format="PNG")
                    buf2.seek(0)
                    logos[n] = tk.PhotoImage(data=buf2.read())
                buf = io.BytesIO()
                Image.merge("RGBA", (shift(r, 0), shift(g, 0), shift(b, 0), a)).save(buf, format="PNG")
                buf.seek(0)
                logos["main"] = tk.PhotoImage(data=buf.read())
                return logos
    except Exception as e:
        print("[WARN] Logo error: " + str(e))
    return None
class OllamaClient:
    def __init__(self):
        self.models = []
    def check(self):
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=5) as r:
                self.models = [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
                return True
        except Exception:
            return False
    def chat(self, model, msg):
        """Non-streaming chat (fallback)"""
        try:
            req = urllib.request.Request("http://localhost:11434/api/chat",
                data=json.dumps({"model": model, "messages": [{"role": "user", "content": msg}], "stream": False}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read().decode().strip()
                lines = data.split('\n')
                first_json = lines[0] if lines else data
                return json.loads(first_json).get("message", {}).get("content", "")
        except Exception as e:
            return "错误：" + str(e)

    def chat_stream(self, model, msg, on_chunk, on_done, on_error):
        """Streaming chat — calls on_chunk(text) per token, on_done() when finished."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/chat",
                data=json.dumps({
                    "model": model,
                    "messages": [{"role": "user", "content": msg}],
                    "stream": True
                }).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                buf = ""
                while True:
                    raw = r.read(1024)
                    if not raw:
                        break
                    buf += raw.decode("utf-8", errors="replace")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            text = obj.get("message", {}).get("content", "")
                            if text:
                                on_chunk(text)
                            if obj.get("done"):
                                on_done()
                                return
                        except json.JSONDecodeError:
                            continue
            on_done()
        except Exception as e:
            on_error(str(e))

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("TuringClaw - 中国电信 AI 助手")
        self.root.geometry("820x700")
        self.root.configure(bg="#1e1e2e")
        self.demo = True
        self.provider = None
        self.model = None
        self.privacy_level = "S1"  # 当前安全级别 S1/S2/S3
        self.ollama = OllamaClient()
        self.logos = load_ct_logo()
        self.history_manager = ChatHistoryManager()
        self._stream_content = ""  # 跟踪流式消息内容
        self.C = {"bg": "#1e1e2e", "bgl": "#313244", "fg": "#cdd6f4", "dim": "#a6adc8",
                  "green": "#a6e3a1", "red": "#f38ba8", "cyan": "#00d4ff", "blue": "#89b4fa",
                  "yellow": "#f9e2af", "purple": "#cba6f7"}
        self.setup_ui()
        self.load_keys()
        self.ollama.check()
        if self.ollama.models:
            print("[OK] Ollama: " + str(self.ollama.models))
        # 初始化聊天历史会话
        provider_name = None
        model_name = None
        if self.provider:
            provider_name = getattr(self.provider, 'name', None) or getattr(self.provider, 'display_name', None)
        if self.model:
            model_name = self.model
        self.history_manager.start_session(provider=provider_name, model=model_name)
        # 窗口关闭时保存会话
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    def setup_ui(self):
        # ========== 1. Top Toolbar ==========
        t = Frame(self.root, bg=self.C["bgl"], height=56)
        t.pack(fill="x")
        t.pack_propagate(False)
        left = Frame(t, bg=self.C["bgl"])
        left.pack(side="left", padx=10, pady=8)
        if self.logos and "main" in self.logos:
            ll = Label(left, image=self.logos["main"], bg=self.C["bgl"])
            ll.image = self.logos["main"]
        else:
            ll = Label(left, text="CT", font=("Arial", 16, "bold"), bg=self.C["bgl"], fg=self.C["cyan"])
        ll.pack(side="left")
        Label(left, text="TuringClaw", font=("Consolas", 15, "bold"), bg=self.C["bgl"], fg=self.C["cyan"]).pack(side="left", padx=8)
        Button(t, text="选择 AI 服务  v", font=("Consolas", 10, "bold"),
               bg=self.C["cyan"], fg="#1e1e2e", bd=0, relief="flat", padx=14, pady=6,
               cursor="hand2", command=self.show_menu).pack(side="left", padx=12)
        self.status = Label(t, text="演示模式", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["green"])
        self.status.pack(side="left", padx=8)
        # 安全级别指示器
        self.privacy_label = Label(t, text="🟢 S1", font=("Consolas", 10, "bold"), bg=self.C["bgl"], fg=self.C["green"])
        self.privacy_label.pack(side="left", padx=8)
        b4 = Button(t, text="用量统计", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
                    bd=0, relief="flat", padx=12, cursor="hand2", command=self.show_usage)
        b4.pack(side="right", padx=8)
        if self.logos and "orange" in self.logos:
            b4.config(image=self.logos["orange"])
            b4.image = self.logos["orange"]
        b5 = Button(t, text="设置", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
                    bd=0, relief="flat", padx=12, cursor="hand2", command=self.show_settings)
        b5.pack(side="right")
        if self.logos and "purple" in self.logos:
            b5.config(image=self.logos["purple"])
            b5.image = self.logos["purple"]
        b6 = Button(t, text="历史", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
                    bd=0, relief="flat", padx=12, cursor="hand2", command=self.show_history)
        b6.pack(side="right")

        # ========== 2. Input Bar (TOP, right below toolbar) ==========
        inp_frame = Frame(self.root, bg=self.C["cyan"], bd=0)
        inp_frame.pack(fill="x", padx=14, pady=(10, 0))
        inp_inner = Frame(inp_frame, bg="#2a2a3c")
        inp_inner.pack(fill="x", padx=2, pady=2)
        lbl = Label(inp_inner, text=">", font=("Consolas", 16, "bold"), bg="#2a2a3c", fg=self.C["cyan"])
        lbl.pack(side="left", padx=(8, 6), pady=8)
        self.inp = Entry(inp_inner, font=("Consolas", 13), bg="#2a2a3c", fg="#cdd6f4",
                        insertbackground=self.C["cyan"], bd=0, relief="flat",
                        highlightthickness=0)
        self.inp.pack(side="left", fill="x", expand=True, ipady=10, pady=8)
        self.inp.insert(0, "在此输入消息…")
        self.inp.config(fg=self.C["dim"])
        self.inp.bind("<Return>", self.send)
        self.inp.bind("<KP_Enter>", self.send)
        self.inp.bind("<FocusIn>", self._on_inp_focus_in)
        self.inp.bind("<FocusOut>", self._on_inp_focus_out)
        btn = Button(inp_inner, text="发送", font=("Consolas", 12, "bold"), bg=self.C["cyan"], fg="#1e1e2e",
                     bd=0, relief="flat", padx=24, pady=8, cursor="hand2", command=self.send)
        btn.pack(side="right", padx=(8, 8), pady=8)

        # ========== 3. Chat Area (fills remaining space below input) ==========
        cf = Frame(self.root, bg=self.C["bg"])
        cf.pack(fill="both", expand=True, padx=14, pady=10)
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)
        self.chat = Text(cf, wrap="word", font=("Consolas", 11), bg="#181825",
                       fg=self.C["fg"], insertbackground=self.C["fg"],
                       bd=0, padx=16, pady=16, state="disabled")
        self.chat.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(cf, command=self.chat.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.chat.config(yscrollcommand=sb.set)
        self.msg("System", "TuringClaw 就绪。点击「选择 AI 服务」配置 Ollama 或云端 AI。")
        self.root.bind("<Escape>", lambda e: self.root.quit())

    def _on_close(self):
        """窗口关闭时保存聊天会话"""
        self.history_manager.end_session()
        self.root.destroy()
    
    def _update_privacy_label(self, level: str):
        """更新安全级别状态指示器"""
        if level == "S1":
            self.privacy_label.config(text="🟢 S1", fg=self.C["green"])
        elif level == "S2":
            self.privacy_label.config(text="🟡 S2", fg=self.C["yellow"])
        elif level == "S3":
            self.privacy_label.config(text="🔴 S3", fg=self.C["red"])
    
    def msg(self, sender, text, color=None):
        self.chat.config(state="normal")
        if color is None:
            color = self.C["yellow"] if sender == "System" else (self.C["blue"] if sender == "You" else self.C["green"])
        self.chat.insert("end", "\n" + sender + ":\n", "t")
        self.chat.tag_config("t", foreground=color, font=("Consolas", 11, "bold"))
        self.chat.insert("end", text + "\n")
        self.chat.see("end")
        self.chat.config(state="disabled")
        # 添加到聊天历史
        role_map = {"System": "system", "You": "user", "TuringClaw": "assistant"}
        role = role_map.get(sender, sender.lower())
        self.history_manager.add_message(role, text)

    def msg_stream_start(self, sender):
        """Initialize streaming message area (replaces 思考中...)"""
        self.chat.config(state="normal")
        self.rm_thinking()
        color = self.C["green"] if sender == "TuringClaw" else self.C["blue"]
        self.chat.insert("end", "\n" + sender + ":\n", "t")
        self.chat.tag_config("t", foreground=color, font=("Consolas", 11, "bold"))
        self.chat.see("end")
        self.chat.config(state="disabled")

    def msg_stream_chunk(self, text):
        """Append a chunk to the current streaming message"""
        self.chat.config(state="normal")
        self.chat.insert("end", text)
        self.chat.see("end")
        self.chat.config(state="disabled")
        # 累积流式消息内容
        self._stream_content += text

    def msg_stream_end(self):
        """Finalize streaming message"""
        self.chat.config(state="normal")
        self.chat.insert("end", "\n")
        self.chat.see("end")
        self.chat.config(state="disabled")
        # 将完整的流式消息保存到历史
        if self._stream_content:
            self.history_manager.add_message("assistant", self._stream_content)
            self._stream_content = ""
    def rm_thinking(self):
        self.chat.config(state="normal")
        for p in ["思考中...", "思考中"]:
            i = self.chat.search(p, "end", backwards=True)
            if i:
                self.chat.delete(i, "end")
        self.chat.config(state="disabled")
    def _on_inp_focus_in(self, e=None):
        if self.inp.get() == "在此输入消息…":
            self.inp.delete(0, "end")
            self.inp.config(fg=self.C["fg"])

    def _on_inp_focus_out(self, e=None):
        if not self.inp.get().strip():
            self.inp.insert(0, "在此输入消息…")
            self.inp.config(fg=self.C["dim"])

    def send(self, e=None):
        msg = self.inp.get().strip()
        if not msg or msg == "在此输入消息…":
            self.inp.delete(0, "end")
            return
        self.inp.delete(0, "end")
        self.inp.config(fg=self.C["dim"])
        self.inp.insert(0, "在此输入消息…")
        self.msg("You", msg)
        # 用户消息已在 msg() 中添加到历史
        self.msg("TuringClaw", "思考中...")
        # Pass current provider/model state to _proc to avoid race conditions
        threading.Thread(target=self._proc, args=(msg, self.provider, self.model, self.demo), daemon=True).start()
    def _proc(self, msg, provider=None, model=None, demo=True):
        try:
            r = ""
            # Use passed parameters instead of self.provider to avoid race conditions
            if provider is None:
                provider = self.provider
            if model is None:
                model = self.model
            
            # ========== 隐私路由 ==========
            actual_msg = msg
            privacy_decision = None
            if privacy_router:
                privacy_decision = privacy_router.route(msg)
                actual_msg = privacy_decision.sanitized_text
                
                # 更新状态栏显示安全级别
                level = privacy_decision.level
                self.root.after(0, lambda l=level: self._update_privacy_label(l))
                
                # 记录审计日志
                if privacy_audit_logger:
                    privacy_audit_logger.log(privacy_decision, msg)
                
                # S3 级别：强制使用本地模型
                if privacy_decision.level == "S3":
                    if not self.ollama.check() or not self.ollama.models:
                        r = "🔒 S3 安全模式要求本地模型，但 Ollama 未运行。\n\n请安装并启动 Ollama:\nhttps://ollama.com/download\n\n然后运行: ollama serve"
                    else:
                        provider = FREE_PROVIDERS.get("ollama") if FREE_PROVIDERS else None
                        model = self.ollama.models[0]
                        demo = False
                        self.root.after(0, lambda: self.status.config(
                            text="🔒 Ollama (S3安全模式)", fg=self.C["green"]))
                        self.root.after(0, lambda: self.msg("System", 
                            f"🔒 S3 安全模式：检测到敏感数据，已自动切换到本地模型处理"))
            
            if provider and provider.name == "ollama":
                if not self.ollama.check() or not self.ollama.models:
                    r = "Ollama 未运行。\n\n安装：https://ollama.com/download/windows\n然后运行：ollama serve"
                    self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", r)))
                else:
                    m = model or self.ollama.models[0]
                    # Streaming output with typewriter effect
                    self.root.after(0, lambda: self.msg_stream_start("TuringClaw"))
                    _out_chars = [0]
                    def _on_chunk(text):
                        _out_chars[0] += len(text)
                        self.root.after(0, lambda t=text: self.msg_stream_chunk(t))
                    def _on_done():
                        if PROVIDERS_AVAILABLE and token_tracker:
                            token_tracker.record_usage("ollama", len(actual_msg)//4, _out_chars[0]//4)
                        self.root.after(0, self.msg_stream_end)
                    def _on_err(e):
                        self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", "错误：" + e)))
                    self.ollama.chat_stream(m, actual_msg, _on_chunk, _on_done, _on_err)
            elif provider:
                r = "[" + provider.display_name + "]\n\n即将支持，目前仅 Ollama 可完整使用。"
                self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", r)))
            else:
                r = self._demo(msg)
                self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", r)))
        except Exception as ex:
            self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", "错误：" + str(ex))))
    def _demo(self, msg):
        m = msg.lower()
        if any(w in m for w in ["hello", "hi", "hey"]):
            return "你好！点击「选择 AI 服务」配置 AI。"
        if any(w in m for w in ["who", "what", "about"]):
            return "TuringClaw - 中国电信 AI 助手，由 Ollama 本地模型驱动。"
        if "help" in m:
            return "功能：代码、问答、本地 AI (Ollama)。点击「选择 AI 服务」开始使用！"
        if "time" in m:
            from datetime import datetime
            return "当前时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if any(o in m for o in ["+", "-", "*", "/"]):
            try:
                expr = "".join(c for c in m if c in "+-*/.0123456789")
                return "计算结果：" + str(eval(expr))
            except Exception:
                return "无法计算此表达式。"
        return "演示模式。您的消息：\"" + msg + "\"\n\n点击「选择 AI 服务」使用 Ollama！"
    def show_menu(self):
        self.ollama.check()
        pop = tk.Toplevel(self.root)
        pop.title("选择 AI 服务")
        pop.geometry("560x520")
        pop.configure(bg=self.C["bg"])
        pop.grab_set()
        Label(pop, text="选择 AI 服务提供商", font=("Consolas", 14, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=15)
        cv = Canvas(pop, bg=self.C["bg"], highlightthickness=0)
        sc = Scrollbar(pop, orient="vertical", command=cv.yview)
        sf = Frame(cv, bg=self.C["bg"])
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=sf.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sc.set)
        o = Frame(sf, bg=self.C["bgl"])
        o.pack(fill="x", padx=10, pady=8)
        Label(o, text="--- 本地模型（免费）---", font=("Consolas", 11, "bold"),
              bg=self.C["bgl"], fg=self.C["cyan"]).pack(anchor="w", padx=14, pady=(12, 6))
        if self.ollama.models:
            s = Frame(o, bg=self.C["bgl"])
            s.pack(fill="x", padx=14, pady=2)
            if self.logos and "green" in self.logos:
                gl = Label(s, image=self.logos["green"], bg=self.C["bgl"])
                gl.image = self.logos["green"]
                gl.pack(side="left")
            Label(s, text="在线  |  " + str(len(self.ollama.models)) + " 个模型", font=("Consolas", 9),
                  bg=self.C["bgl"], fg=self.C["green"]).pack(side="left", padx=4)
            Label(o, text=" / ".join(self.ollama.models[:5]), font=("Consolas", 8),
                  bg=self.C["bgl"], fg=self.C["dim"], wraplength=480, justify="left").pack(anchor="w", padx=14, pady=(0, 4))
            mf = Frame(o, bg=self.C["bgl"])
            mf.pack(anchor="w", padx=14, pady=6)
            Label(mf, text="模型：", font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["fg"]).pack(side="left")
            mv = StringVar(value=self.ollama.models[0])
            cb = ttk.Combobox(mf, textvariable=mv, values=self.ollama.models, state="readonly", font=("Consolas", 9), width=30)
            cb.pack(side="left", padx=6)
            bf = Frame(o, bg=self.C["bgl"])
            bf.pack(anchor="w", padx=14, pady=(4, 12))
            Button(bf, text="使用 Ollama", font=("Consolas", 10, "bold"), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=20, pady=6, cursor="hand2",
                   command=lambda p=pop: self._use_ollama(mv.get(), p)).pack(side="left")
        else:
            s = Frame(o, bg=self.C["bgl"])
            s.pack(fill="x", padx=14, pady=4)
            if self.logos and "red" in self.logos:
                rl = Label(s, image=self.logos["red"], bg=self.C["bgl"])
                rl.image = self.logos["red"]
                rl.pack(side="left")
            Label(s, text="未运行", font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["red"]).pack(side="left", padx=4)
            Button(o, text="安装 Ollama（免费）", font=("Consolas", 10, "bold"), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=14, pady=6, cursor="hand2",
                   command=lambda: messagebox.showinfo("安装 Ollama",
                       "Windows: https://ollama.com/download/windows\nmacOS: brew install ollama\nLinux: curl -fsSL https://ollama.com/install.sh | sh\n\n然后运行：ollama serve")).pack(anchor="w", padx=14, pady=(4, 0))
            Label(o, text="然后运行：ollama serve", font=("Consolas", 8),
                  bg=self.C["bgl"], fg=self.C["dim"]).pack(anchor="w", padx=14, pady=(0, 12))
        Label(sf, text="--- 云端服务（需 API Key）---", bg=self.C["bg"],
              fg=self.C["dim"], font=("Consolas", 10)).pack(pady=(10, 5))
        if PROVIDERS_AVAILABLE:
            for n, p in get_all_providers_status().items():
                if n != "ollama":
                    self._make_card(sf, p, pop)
        cv.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=10)
        sc.pack(side="right", fill="y", pady=10, padx=(0, 14))
        def _close_menu():
            try: pop.grab_release()
            except Exception: pass
            pop.destroy()
            self.root.after(50, self.inp.focus_set)
        Button(pop, text="关闭", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=_close_menu).pack(pady=10)
    def _use_ollama(self, model, pop):
        if not model:
            return
        # Set Ollama provider (works even without providers.py module)
        try:
            if PROVIDERS_AVAILABLE and FREE_PROVIDERS.get("ollama"):
                self.provider = FREE_PROVIDERS["ollama"]
            else:
                # Fallback: create a minimal ProviderInfo so _proc recognizes it
                try:
                    from gui.providers import ProviderInfo
                except ImportError:
                    try:
                        from providers import ProviderInfo
                    except ImportError:
                        class ProviderInfo:
                            def __init__(self, **kw):
                                for k, v in kw.items():
                                    setattr(self, k, v)
                self.provider = ProviderInfo(
                    name="ollama", display_name="Ollama",
                    api_key_env="OLLAMA_API_KEY", is_local=True, status="configured")
        except Exception as e:
            messagebox.showerror("错误", "Failed to set provider: " + str(e))
            return
        self.model = model
        self.demo = False
        self.status.config(text="Ollama (" + model + ")", fg=self.C["green"])
        self.rm_thinking()
        self.msg("System", "已连接 Ollama：" + model + "。开始聊天！")
        try: pop.grab_release()
        except Exception: pass
        pop.destroy()
        self.root.after(50, self.inp.focus_set)
    def _make_card(self, parent, provider, pop):
        c = Frame(parent, bg=self.C["bgl"])
        c.pack(fill="x", padx=10, pady=4)
        Label(c, text=provider.display_name, font=("Consolas", 11, "bold"),
              bg=self.C["bgl"], fg=self.C["fg"], anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        Label(c, text="免费额度：" + provider.free_tier, font=("Consolas", 9),
              bg=self.C["bgl"], fg=self.C["dim"], anchor="w").pack(fill="x", padx=14)
        bf = Frame(c, bg=self.C["bgl"])
        bf.pack(fill="x", padx=14, pady=(6, 10))
        if provider.status == "configured":
            def do_use():
                setattr(self, "provider", provider)
                setattr(self, "demo", False)
                self.status.config(text=provider.display_name, fg=self.C["green"])
                try: pop.grab_release()
                except Exception: pass
                pop.destroy()
                self.msg("System", "已切换至 " + provider.display_name)
                self.root.after(50, self.inp.focus_set)
            Button(bf, text="使用", font=("Consolas", 9), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=14, pady=3, cursor="hand2", command=do_use).pack(side="left")
            Label(bf, text="已配置", font=("Consolas", 9, "bold"), bg=self.C["bgl"], fg=self.C["green"]).pack(side="right")
        else:
            Button(bf, text="配置 API", font=("Consolas", 9), bg=self.C["cyan"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=12, pady=3, cursor="hand2",
                   command=lambda: self._config_api(provider, pop)).pack(side="left")
            def open_signup():
                try:
                    import webbrowser
                    webbrowser.open(provider.signup_url)
                except Exception as e:
                    messagebox.showerror("错误", "Could not open browser: " + str(e))
            Button(bf, text="注册", font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                   bd=0, relief="flat", padx=10, pady=3, cursor="hand2",
                   command=open_signup).pack(side="left", padx=4)
    def _config_api(self, provider, pop):
        k = simpledialog.askstring("配置 " + provider.display_name,
                                   "输入 API Key：\n\n注册地址：" + provider.signup_url, show="*")
        if k:
            os.environ[provider.api_key_env] = k
            d = Path.home() / ".TuringClaw"
            d.mkdir(exist_ok=True)
            f = d / "api_keys.json"
            ks = {}
            if f.exists():
                try:
                    ks = json.loads(f.read_text())
                except Exception as e:
                    print("[WARN] Could not load api_keys.json: " + str(e))
            ks[provider.name] = k
            f.write_text(json.dumps(ks, indent=2))
            messagebox.showinfo("完成", "API Key 已保存：" + provider.display_name + "！")
            try: pop.grab_release()
            except Exception: pass
            pop.destroy()
            self.root.after(50, self.inp.focus_set)
    def load_keys(self):
        f = Path.home() / ".TuringClaw" / "api_keys.json"
        if not f.exists():
            return
        try:
            for pn, k in json.loads(f.read_text()).items():
                for n, p in FREE_PROVIDERS.items():
                    if p.name == pn:
                        os.environ[p.api_key_env] = k
        except Exception as e:
            print("[WARN] Could not load api_keys.json: " + str(e))
    def show_usage(self):
        if not PROVIDERS_AVAILABLE:
            messagebox.showinfo("信息", "用量统计模块不可用")
            return
        pop = tk.Toplevel(self.root)
        pop.title("Token 用量统计")
        pop.geometry("460x400")
        pop.configure(bg=self.C["bg"])
        Label(pop, text="Token 用量统计", font=("Consolas", 14, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=15)
        u = token_tracker.get_usage()
        if not u:
            Label(pop, text="暂无用量数据。\n与 AI 对话后即可查看统计。",
                  font=("Consolas", 11), bg=self.C["bg"], fg=self.C["dim"]).pack(pady=40)
        else:
            cv = Canvas(pop, bg=self.C["bg"], highlightthickness=0)
            sc = Scrollbar(pop, orient="vertical", command=cv.yview)
            sf = Frame(cv, bg=self.C["bg"])
            sf.bind("<Configure>", lambda e: cv.configure(scrollregion=sf.bbox("all")))
            cv.create_window((0, 0), window=sf, anchor="nw")
            cv.configure(yscrollcommand=sc.set)
            for pn, d in u.items():
                c = Frame(sf, bg=self.C["bgl"])
                c.pack(fill="x", padx=10, pady=4)
                Label(c, text=pn, font=("Consolas", 11, "bold"),
                      bg=self.C["bgl"], fg=self.C["fg"]).pack(anchor="w", padx=14, pady=(10, 2))
                i, o = d.get("total_input", 0), d.get("total_output", 0)
                Label(c, text="输入：" + str(i) + "  |  输出：" + str(o) + "  |  合计：" + str(i+o) + " tokens  |  请求数：" + str(d.get("total_requests", 0)),
                      font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["dim"]).pack(anchor="w", padx=14, pady=(0, 10))
            cv.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=10)
            sc.pack(side="right", fill="y", pady=10, padx=(0, 14))
        def _close_usage():
            try: pop.grab_release()
            except Exception: pass
            pop.destroy()
            self.root.after(50, self.inp.focus_set)
        Button(pop, text="关闭", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=_close_usage).pack(pady=10)
    def show_settings(self):
        pop = tk.Toplevel(self.root)
        pop.title("设置")
        pop.geometry("450x400")
        pop.configure(bg=self.C["bg"])
        Label(pop, text="设置", font=("Consolas", 14, "bold"), bg=self.C["bg"], fg=self.C["fg"]).pack(pady=15)
        Label(pop, text="TuringClaw v2.0.0\n中国电信 AI 助手\n由 Ollama + 隐私路由驱动",
              font=("Consolas", 10), bg=self.C["bg"], fg=self.C["dim"], justify="center").pack(pady=10)
        
        # 安全级别设置
        Label(pop, text="─" * 40, bg=self.C["bg"], fg=self.C["dim"]).pack(pady=5)
        Label(pop, text="🔒 Privacy Level (安全级别)", font=("Consolas", 11, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=5)
        
        level_frame = Frame(pop, bg=self.C["bg"])
        level_frame.pack(pady=5)
        
        current_level = self.privacy_level
        level_var = StringVar(value=current_level)
        
        def set_level(l):
            self.privacy_level = l
            if privacy_router:
                if l == "AUTO":
                    privacy_router.set_manual_level(None)
                else:
                    privacy_router.set_manual_level(l)
            self._update_privacy_label(l if l != "AUTO" else "S1")
            messagebox.showinfo("隐私级别", f"安全级别已设置为: {l}")
        
        Radiobutton(level_frame, text="🟢 S1 正常模式", variable=level_var, value="S1",
                    bg=self.C["bg"], fg=self.C["green"], selectcolor=self.C["bgl"],
                    command=lambda: set_level("S1")).pack(anchor="w")
        Radiobutton(level_frame, text="🟡 S2 脱敏模式", variable=level_var, value="S2",
                    bg=self.C["bg"], fg=self.C["yellow"], selectcolor=self.C["bgl"],
                    command=lambda: set_level("S2")).pack(anchor="w")
        Radiobutton(level_frame, text="🔴 S3 安全模式 (仅本地)", variable=level_var, value="S3",
                    bg=self.C["bg"], fg=self.C["red"], selectcolor=self.C["bgl"],
                    command=lambda: set_level("S3")).pack(anchor="w")
        Radiobutton(level_frame, text="⚡ 自动检测 (推荐)", variable=level_var, value="AUTO",
                    bg=self.C["bg"], fg=self.C["cyan"], selectcolor=self.C["bgl"],
                    command=lambda: set_level("AUTO")).pack(anchor="w")
        
        Label(pop, text="─" * 40, bg=self.C["bg"], fg=self.C["dim"]).pack(pady=5)
        
        def do_reset():
            setattr(self, "demo", True)
            setattr(self, "provider", None)
            setattr(self, "model", None)
            self.status.config(text="演示模式", fg=self.C["green"])
            pop.destroy()
            self.rm_thinking()
            self.msg("System", "已切换为演示模式")
        Button(pop, text="重置为演示模式", font=("Consolas", 10), bg=self.C["red"], fg="white",
               bd=0, relief="flat", padx=14, pady=5, cursor="hand2", command=do_reset).pack(pady=8)
        def _close_settings():
            try: pop.grab_release()
            except Exception: pass
            pop.destroy()
            self.root.after(50, self.inp.focus_set)
        Button(pop, text="关闭", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=_close_settings).pack(pady=8)

    def show_history(self):
        """弹出历史会话列表窗口"""
        pop = tk.Toplevel(self.root)
        pop.title("聊天历史")
        pop.geometry("680x520")
        pop.configure(bg=self.C["bg"])
        pop.grab_set()

        # 标题
        Label(pop, text="📋 聊天历史", font=("Consolas", 14, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=10)

        # 搜索栏
        search_frame = Frame(pop, bg=self.C["bgl"])
        search_frame.pack(fill="x", padx=14, pady=(0, 6))
        Label(search_frame, text="🔍", font=("Consolas", 12), bg=self.C["bgl"], fg=self.C["fg"]).pack(side="left", padx=6)
        search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=search_var, font=("Consolas", 11),
                            bg="#2a2a3c", fg=self.C["fg"], insertbackground=self.C["cyan"],
                            bd=0, relief="flat")
        search_entry.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        search_entry.insert(0, "搜索历史消息…")
        search_entry.config(fg=self.C["dim"])
        search_entry.bind("<FocusIn>", lambda e: (
            search_entry.delete(0, "end") if search_var.get() == "搜索历史消息…" else None,
            search_entry.config(fg=self.C["fg"]) if search_var.get() == "搜索历史消息…" else None
        ))

        # 会话列表区域
        list_container = Frame(pop, bg=self.C["bg"])
        list_container.pack(fill="both", expand=True, padx=14, pady=4)
        cv = Canvas(list_container, bg=self.C["bg"], highlightthickness=0)
        sb = Scrollbar(list_container, orient="vertical", command=cv.yview)
        list_frame = Frame(cv, bg=self.C["bg"])
        list_frame.bind("<Configure>", lambda e: cv.configure(scrollregion=list_frame.bbox("all")))
        cv.create_window((0, 0), window=list_frame, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def refresh_list():
            for w in list_frame.winfo_children():
                w.destroy()
            sessions = self.history_manager.list_sessions(limit=20)
            if not sessions:
                Label(list_frame, text="暂无聊天记录", font=("Consolas", 11),
                      bg=self.C["bg"], fg=self.C["dim"]).pack(pady=20)
                return
            for s in sessions:
                card = Frame(list_frame, bg=self.C["bgl"], cursor="hand2")
                card.pack(fill="x", padx=6, pady=3)
                time_str = s.get("start_time", "")[:19].replace("T", " ")
                info_frame = Frame(card, bg=self.C["bgl"])
                info_frame.pack(fill="x", padx=10, pady=(8, 0))
                Label(info_frame, text=f"📅 {time_str}", font=("Consolas", 10, "bold"),
                      bg=self.C["bgl"], fg=self.C["fg"]).pack(side="left")
                Label(info_frame, text=f"  📦 {s.get('model', '未知')}", font=("Consolas", 9),
                      bg=self.C["bgl"], fg=self.C["dim"]).pack(side="left")
                Label(info_frame, text=f"  💬 {s.get('message_count', 0)}条", font=("Consolas", 9),
                      bg=self.C["bgl"], fg=self.C["dim"]).pack(side="left")
                # 预览
                preview = s.get("preview", "")
                if preview:
                    Label(card, text=preview, font=("Consolas", 9), bg=self.C["bgl"],
                          fg=self.C["dim"], wraplength=580, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
                # 双击加载该会话
                f_path = s.get("file", "")
                card.bind("<Double-Button-1>", lambda e, fp=f_path: self._load_history_to_chat(fp, pop))
                for child in card.winfo_children():
                    child.bind("<Double-Button-1>", lambda e, fp=f_path: self._load_history_to_chat(fp, pop))
                # 右键菜单（删除/导出）
                def make_menu(fp, card_w=card):
                    menu = tk.Menu(card_w, tearoff=0, bg=self.C["bgl"], fg=self.C["fg"])
                    menu.add_command(label="删除此会话", command=lambda: self._delete_history_session(fp, card_w, list_frame))
                    menu.add_command(label="导出为 TXT", command=lambda: self._export_history_session(fp, "txt"))
                    menu.add_command(label="导出为 Markdown", command=lambda: self._export_history_session(fp, "md"))
                    return menu
                card.bind("<Button-3>", lambda e, fp=f_path: make_menu(fp).tk_popup(e.x_root, e.y_root))

        def do_search(*_):
            kw = search_var.get().strip()
            if not kw or kw == "搜索历史消息…":
                refresh_list()
                return
            for w in list_frame.winfo_children():
                w.destroy()
            results = self.history_manager.search_messages(kw, limit=10)
            if not results:
                Label(list_frame, text="未找到匹配的消息", font=("Consolas", 11),
                      bg=self.C["bg"], fg=self.C["dim"]).pack(pady=20)
                return
            for r in results:
                card = Frame(list_frame, bg=self.C["bgl"], cursor="hand2")
                card.pack(fill="x", padx=6, pady=3)
                time_str = r.get("start_time", "")[:19].replace("T", " ")
                role_icon = "👤" if r.get("role") == "user" else "🤖"
                Label(card, text=f"{time_str}  |  {r.get('model', '未知')}  |  {role_icon} {r.get('role', '')}",
                      font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["dim"]).pack(anchor="w", padx=10, pady=(6, 0))
                Label(card, text=r.get("content", "")[:80], font=("Consolas", 10),
                      bg=self.C["bgl"], fg=self.C["fg"], wraplength=580, justify="left").pack(anchor="w", padx=10, pady=(0, 6))
                f_path = r.get("file", "")
                card.bind("<Double-Button-1>", lambda e, fp=f_path: self._load_history_to_chat(fp, pop))
                for child in card.winfo_children():
                    child.bind("<Double-Button-1>", lambda e, fp=f_path: self._load_history_to_chat(fp, pop))

        search_var.trace_add("write", do_search)
        refresh_list()

        # 底部按钮
        btn_frame = Frame(pop, bg=self.C["bg"])
        btn_frame.pack(fill="x", padx=14, pady=8)
        def _close_history():
            try: pop.grab_release()
            except Exception: pass
            pop.destroy()
            self.root.after(50, self.inp.focus_set)
        Button(btn_frame, text="关闭", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, cursor="hand2", command=_close_history).pack(side="right")

    def _load_history_to_chat(self, session_file, pop):
        """加载历史会话到当前聊天区域"""
        data = self.history_manager.load_session(session_file)
        if not data:
            messagebox.showwarning("提示", "无法加载该会话记录")
            return
        # 清空当前聊天区
        self.chat.config(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.config(state="disabled")
        # 重放消息
        for msg in data.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            sender_map = {"user": "You", "assistant": "TuringClaw", "system": "System"}
            sender = sender_map.get(role, role)
            self.chat.config(state="normal")
            color = self.C["yellow"] if sender == "System" else (self.C["blue"] if sender == "You" else self.C["green"])
            self.chat.insert("end", "\n" + sender + ":\n", "t")
            self.chat.tag_config("t", foreground=color, font=("Consolas", 11, "bold"))
            self.chat.insert("end", content + "\n")
            self.chat.see("end")
            self.chat.config(state="disabled")
        # 关闭历史窗口
        try: pop.grab_release()
        except Exception: pass
        pop.destroy()

    def _delete_history_session(self, session_file, card_widget, list_frame):
        """删除历史会话"""
        if messagebox.askyesno("确认删除", "确定要删除此会话记录吗？"):
            self.history_manager.delete_session(session_file)
            card_widget.destroy()
            if not list_frame.winfo_children():
                Label(list_frame, text="暂无聊天记录", font=("Consolas", 11),
                      bg=self.C["bg"], fg=self.C["dim"]).pack(pady=20)

    def _export_history_session(self, session_file, fmt):
        """导出历史会话"""
        from tkinter import filedialog
        data = self.history_manager.load_session(session_file)
        if not data:
            messagebox.showwarning("提示", "无法加载该会话记录")
            return
        session_id = data.get("session_id", "export")
        ext = ".md" if fmt == "md" else ".txt"
        default_name = f"chat_{session_id}{ext}"
        export_path = filedialog.asksaveasfilename(
            title="导出聊天记录",
            defaultextension=ext,
            initialfile=default_name,
            filetypes=[("文本文件", "*.txt"), ("Markdown", "*.md")] if fmt == "md" else [("文本文件", "*.txt")]
        )
        if export_path:
            if self.history_manager.export_session(session_file, export_path, format=fmt):
                messagebox.showinfo("导出成功", f"聊天记录已导出到:\n{export_path}")
            else:
                messagebox.showerror("导出失败", "无法导出聊天记录")

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
if __name__ == "__main__":
    main()
