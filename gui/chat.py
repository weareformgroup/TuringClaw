
#!/usr/bin/env python3
# TuringClaw GUI - China Telecom AI Assistant
import os, sys, threading, json, io, urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Text, Entry, Frame, Label, Button, Canvas, Scrollbar, StringVar
try:
    from gui.providers import FREE_PROVIDERS, get_all_providers_status, TokenTracker, token_tracker
    PROVIDERS_AVAILABLE = True
except ImportError:
    PROVIDERS_AVAILABLE = False
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
        try:
            req = urllib.request.Request("http://localhost:11434/api/chat",
                data=json.dumps({"model": model, "messages": [{"role": "user", "content": msg}], "stream": False}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read().decode().strip()
                # Handle potential multiple JSON responses
                lines = data.split('\n')
                first_json = lines[0] if lines else data
                return json.loads(first_json).get("message", {}).get("content", "")
        except Exception as e:
            return "Error: " + str(e)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("TuringClaw - China Telecom AI")
        self.root.geometry("820x700")
        self.root.configure(bg="#1e1e2e")
        self.demo = True
        self.provider = None
        self.model = None
        self.ollama = OllamaClient()
        self.logos = load_ct_logo()
        self.C = {"bg": "#1e1e2e", "bgl": "#313244", "fg": "#cdd6f4", "dim": "#a6adc8",
                  "green": "#a6e3a1", "red": "#f38ba8", "cyan": "#00d4ff", "blue": "#89b4fa",
                  "yellow": "#f9e2af", "purple": "#cba6f7"}
        self.setup_ui()
        self.load_keys()
        self.ollama.check()
        if self.ollama.models:
            print("[OK] Ollama: " + str(self.ollama.models))
    def setup_ui(self):
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
        Button(t, text="Select AI Provider  v", font=("Consolas", 10, "bold"),
               bg=self.C["cyan"], fg="#1e1e2e", bd=0, relief="flat", padx=14, pady=6,
               cursor="hand2", command=self.show_menu).pack(side="left", padx=12)
        self.status = Label(t, text="Demo Mode", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["green"])
        self.status.pack(side="left", padx=8)
        b4 = Button(t, text="Usage", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
                    bd=0, relief="flat", padx=12, cursor="hand2", command=self.show_usage)
        b4.pack(side="right", padx=8)
        if self.logos and "orange" in self.logos:
            b4.config(image=self.logos["orange"])
            b4.image = self.logos["orange"]
        b5 = Button(t, text="Settings", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
                    bd=0, relief="flat", padx=12, cursor="hand2", command=self.show_settings)
        b5.pack(side="right")
        if self.logos and "purple" in self.logos:
            b5.config(image=self.logos["purple"])
            b5.image = self.logos["purple"]
        cf = Frame(self.root, bg=self.C["bg"])
        cf.pack(fill="both", expand=True, padx=14, pady=14)
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)
        self.chat = Text(cf, wrap="word", font=("Consolas", 11), bg="#181825",
                       fg=self.C["fg"], insertbackground=self.C["fg"],
                       bd=0, padx=16, pady=16, state="disabled")
        self.chat.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(cf, command=self.chat.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.chat.config(yscrollcommand=sb.set)
        inp = Frame(self.root, bg=self.C["bg"])
        inp.pack(fill="x", padx=14, pady=(0, 14))
        self.inp = Entry(inp, font=("Consolas", 12), bg=self.C["bgl"], fg=self.C["fg"],
                        insertbackground=self.C["fg"], bd=0, relief="flat",
                        highlightthickness=1, highlightcolor=self.C["cyan"], highlightbackground="#45475a")
        self.inp.pack(side="left", fill="x", expand=True)
        self.inp.bind("<Return>", self.send)
        self.inp.bind("<KP_Enter>", self.send)
        self.inp.focus()
        Button(inp, text="Send", font=("Consolas", 11, "bold"), bg=self.C["cyan"], fg="#1e1e2e",
               bd=0, relief="flat", padx=20, pady=8, cursor="hand2", command=self.send).pack(side="right", padx=(10, 0))
        self.msg("System", "TuringClaw Ready. Click 'Select AI Provider' to configure Ollama or cloud AI.")
        self.root.bind("<Escape>", lambda e: self.root.quit())
    def msg(self, sender, text, color=None):
        self.chat.config(state="normal")
        if color is None:
            color = self.C["yellow"] if sender == "System" else (self.C["blue"] if sender == "You" else self.C["green"])
        self.chat.insert("end", "\n" + sender + ":\n", "t")
        self.chat.tag_config("t", foreground=color, font=("Consolas", 11, "bold"))
        self.chat.insert("end", text + "\n")
        self.chat.see("end")
        self.chat.config(state="disabled")
    def rm_thinking(self):
        self.chat.config(state="normal")
        for p in ["Thinking...", "Thinking"]:
            i = self.chat.search(p, "end", backwards=True)
            if i:
                self.chat.delete(i, "end")
        self.chat.config(state="disabled")
    def send(self, e=None):
        msg = self.inp.get().strip()
        if not msg:
            return
        self.inp.delete(0, "end")
        self.msg("You", msg)
        self.msg("TuringClaw", "Thinking...")
        # Pass current provider/model state to _proc to avoid race conditions
        print(f"[DEBUG send] provider={self.provider}, model={self.model}, demo={self.demo}")
        threading.Thread(target=self._proc, args=(msg, self.provider, self.model, self.demo), daemon=True).start()
    def _proc(self, msg, provider=None, model=None, demo=True):
        try:
            r = ""
            print(f"[DEBUG _proc] received: provider={provider}, model={model}, demo={demo}")
            # Use passed parameters instead of self.provider to avoid race conditions
            if provider is None:
                provider = self.provider
                print(f"[DEBUG _proc] provider was None, using self.provider={provider}")
            if model is None:
                model = self.model
                print(f"[DEBUG _proc] model was None, using self.model={model}")
            
            print(f"[DEBUG _proc] final: provider={provider}, model={model}")
            if provider and provider.name == "ollama":
                print(f"[DEBUG _proc] Using Ollama")
                if not self.ollama.check() or not self.ollama.models:
                    r = "Ollama not running.\n\nInstall: https://ollama.com/download/windows\nThen run: ollama serve"
                else:
                    m = model or self.ollama.models[0]
                    print(f"[DEBUG _proc] Calling ollama.chat with model={m}")
                    r = self.ollama.chat(m, msg)
                    if PROVIDERS_AVAILABLE and token_tracker:
                        token_tracker.record_usage("ollama", len(msg)//4, len(r)//4)
            elif provider:
                print(f"[DEBUG _proc] Using provider {provider.display_name}")
                r = "[" + provider.display_name + "]\n\nComing soon. Only Ollama is fully supported."
            else:
                print(f"[DEBUG _proc] Using demo mode")
                r = self._demo(msg)
            self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", r)))
        except Exception as ex:
            print(f"[ERROR _proc] {ex}")
            self.root.after(0, lambda: (self.rm_thinking(), self.msg("TuringClaw", "Error: " + str(ex))))
    def _demo(self, msg):
        m = msg.lower()
        if any(w in m for w in ["hello", "hi", "hey"]):
            return "Hello! Click 'Select AI Provider' to configure AI."
        if any(w in m for w in ["who", "what", "about"]):
            return "TuringClaw - China Telecom AI. Powered by Ollama local models."
        if "help" in m:
            return "Features: Code, Q&A, Local AI (Ollama). Click 'Select AI Provider' to get started!"
        if "time" in m:
            from datetime import datetime
            return "Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if any(o in m for o in ["+", "-", "*", "/"]):
            try:
                expr = "".join(c for c in m if c in "+-*/.0123456789")
                return "Result: " + str(eval(expr))
            except Exception:
                return "Cannot calculate that."
        return "Demo mode. Your message: \"" + msg + "\"\n\nClick \"Select AI Provider\" to use Ollama!"
    def show_menu(self):
        self.ollama.check()
        pop = tk.Toplevel(self.root)
        pop.title("Select AI Provider")
        pop.geometry("560x520")
        pop.configure(bg=self.C["bg"])
        pop.grab_set()
        Label(pop, text="Select AI Service Provider", font=("Consolas", 14, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=15)
        cv = Canvas(pop, bg=self.C["bg"], highlightthickness=0)
        sc = Scrollbar(pop, orient="vertical", command=cv.yview)
        sf = Frame(cv, bg=self.C["bg"])
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=sf.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sc.set)
        o = Frame(sf, bg=self.C["bgl"])
        o.pack(fill="x", padx=10, pady=8)
        Label(o, text="--- LOCAL MODELS (Free) ---", font=("Consolas", 11, "bold"),
              bg=self.C["bgl"], fg=self.C["cyan"]).pack(anchor="w", padx=14, pady=(12, 6))
        if self.ollama.models:
            s = Frame(o, bg=self.C["bgl"])
            s.pack(fill="x", padx=14, pady=2)
            if self.logos and "green" in self.logos:
                gl = Label(s, image=self.logos["green"], bg=self.C["bgl"])
                gl.image = self.logos["green"]
                gl.pack(side="left")
            Label(s, text="Online  |  " + str(len(self.ollama.models)) + " models", font=("Consolas", 9),
                  bg=self.C["bgl"], fg=self.C["green"]).pack(side="left", padx=4)
            Label(o, text=" / ".join(self.ollama.models[:5]), font=("Consolas", 8),
                  bg=self.C["bgl"], fg=self.C["dim"], wraplength=480, justify="left").pack(anchor="w", padx=14, pady=(0, 4))
            mf = Frame(o, bg=self.C["bgl"])
            mf.pack(anchor="w", padx=14, pady=6)
            Label(mf, text="Model:", font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["fg"]).pack(side="left")
            mv = StringVar(value=self.ollama.models[0])
            cb = ttk.Combobox(mf, textvariable=mv, values=self.ollama.models, state="readonly", font=("Consolas", 9), width=30)
            cb.pack(side="left", padx=6)
            bf = Frame(o, bg=self.C["bgl"])
            bf.pack(anchor="w", padx=14, pady=(4, 12))
            Button(bf, text="Use Ollama", font=("Consolas", 10, "bold"), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=20, pady=6, cursor="hand2",
                   command=lambda m=mv.get(), p=pop: self._use_ollama(m, p)).pack(side="left")
        else:
            s = Frame(o, bg=self.C["bgl"])
            s.pack(fill="x", padx=14, pady=4)
            if self.logos and "red" in self.logos:
                rl = Label(s, image=self.logos["red"], bg=self.C["bgl"])
                rl.image = self.logos["red"]
                rl.pack(side="left")
            Label(s, text="Not Running", font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["red"]).pack(side="left", padx=4)
            Button(o, text="Install Ollama (Free)", font=("Consolas", 10, "bold"), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=14, pady=6, cursor="hand2",
                   command=lambda: messagebox.showinfo("Install Ollama",
                       "Windows: https://ollama.com/download/windows\nmacOS: brew install ollama\nLinux: curl -fsSL https://ollama.com/install.sh | sh\n\nThen run: ollama serve")).pack(anchor="w", padx=14, pady=(4, 0))
            Label(o, text="Then run: ollama serve", font=("Consolas", 8),
                  bg=self.C["bgl"], fg=self.C["dim"]).pack(anchor="w", padx=14, pady=(0, 12))
        Label(sf, text="--- CLOUD PROVIDERS (API Key) ---", bg=self.C["bg"],
              fg=self.C["dim"], font=("Consolas", 10)).pack(pady=(10, 5))
        if PROVIDERS_AVAILABLE:
            for n, p in get_all_providers_status().items():
                if n != "ollama":
                    self._make_card(sf, p, pop)
        cv.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=10)
        sc.pack(side="right", fill="y", pady=10, padx=(0, 14))
        Button(pop, text="Close", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=pop.destroy).pack(pady=10)
    def _use_ollama(self, model, pop):
        if not model:
            return
        print(f"[DEBUG _use_ollama] Called with model={model}")
        if PROVIDERS_AVAILABLE:
            self.provider = list(FREE_PROVIDERS.values())[0]
            print(f"[DEBUG _use_ollama] Set self.provider={self.provider.name}")
        self.model = model
        self.demo = False
        print(f"[DEBUG _use_ollama] Set self.model={model}, self.demo=False")
        self.status.config(text="Ollama (" + model + ")", fg=self.C["green"])
        self.rm_thinking()
        self.msg("System", "Connected to Ollama: " + model + ". Start chatting!")
        try:
            pop.destroy()
            print(f"[DEBUG _use_ollama] Destroyed pop window")
        except Exception as e:
            print(f"[DEBUG _use_ollama] Error destroying pop: {e}")
        print(f"[DEBUG _use_ollama] Final state: provider={self.provider}, model={self.model}, demo={self.demo}")
    def _make_card(self, parent, provider, pop):
        c = Frame(parent, bg=self.C["bgl"])
        c.pack(fill="x", padx=10, pady=4)
        Label(c, text=provider.display_name, font=("Consolas", 11, "bold"),
              bg=self.C["bgl"], fg=self.C["fg"], anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        Label(c, text="Free: " + provider.free_tier, font=("Consolas", 9),
              bg=self.C["bgl"], fg=self.C["dim"], anchor="w").pack(fill="x", padx=14)
        bf = Frame(c, bg=self.C["bgl"])
        bf.pack(fill="x", padx=14, pady=(6, 10))
        if provider.status == "configured":
            def do_use():
                setattr(self, "provider", provider)
                setattr(self, "demo", False)
                self.status.config(text=provider.display_name, fg=self.C["green"])
                pop.destroy()
                self.msg("System", "Switched to " + provider.display_name)
            Button(bf, text="Use", font=("Consolas", 9), bg=self.C["green"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=14, pady=3, cursor="hand2", command=do_use).pack(side="left")
            Label(bf, text="Configured", font=("Consolas", 9, "bold"), bg=self.C["bgl"], fg=self.C["green"]).pack(side="right")
        else:
            Button(bf, text="Config API", font=("Consolas", 9), bg=self.C["cyan"], fg="#1e1e2e",
                   bd=0, relief="flat", padx=12, pady=3, cursor="hand2",
                   command=lambda: self._config_api(provider, pop)).pack(side="left")
            def open_signup():
                try:
                    import webbrowser
                    webbrowser.open(provider.signup_url)
                except Exception as e:
                    messagebox.showerror("Error", "Could not open browser: " + str(e))
            Button(bf, text="Sign Up", font=("Consolas", 9), bg=self.C["bg"], fg=self.C["fg"],
                   bd=0, relief="flat", padx=10, pady=3, cursor="hand2",
                   command=open_signup).pack(side="left", padx=4)
    def _config_api(self, provider, pop):
        k = simpledialog.askstring("Config " + provider.display_name,
                                   "Enter API Key:\n\nURL: " + provider.signup_url, show="*")
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
            messagebox.showinfo("Done", "API Key saved for " + provider.display_name + "!")
            pop.destroy()
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
            messagebox.showinfo("Info", "Usage module not available")
            return
        pop = tk.Toplevel(self.root)
        pop.title("Token Usage")
        pop.geometry("460x400")
        pop.configure(bg=self.C["bg"])
        Label(pop, text="Token Usage Statistics", font=("Consolas", 14, "bold"),
              bg=self.C["bg"], fg=self.C["cyan"]).pack(pady=15)
        u = token_tracker.get_usage()
        if not u:
            Label(pop, text="No usage data yet.\nChat with AI to see stats.",
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
                Label(c, text="Input: " + str(i) + "  |  Output: " + str(o) + "  |  Total: " + str(i+o) + " tokens  |  Requests: " + str(d.get("total_requests", 0)),
                      font=("Consolas", 9), bg=self.C["bgl"], fg=self.C["dim"]).pack(anchor="w", padx=14, pady=(0, 10))
            cv.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=10)
            sc.pack(side="right", fill="y", pady=10, padx=(0, 14))
        Button(pop, text="Close", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=pop.destroy).pack(pady=10)
    def show_settings(self):
        pop = tk.Toplevel(self.root)
        pop.title("Settings")
        pop.geometry("400x300")
        pop.configure(bg=self.C["bg"])
        Label(pop, text="Settings", font=("Consolas", 14, "bold"), bg=self.C["bg"], fg=self.C["fg"]).pack(pady=15)
        Label(pop, text="TuringClaw v0.2.0\nChina Telecom AI\nPowered by Ollama",
              font=("Consolas", 10), bg=self.C["bg"], fg=self.C["dim"], justify="center").pack(pady=20)
        def do_reset():
            setattr(self, "demo", True)
            setattr(self, "provider", None)
            setattr(self, "model", None)
            self.status.config(text="Demo Mode", fg=self.C["green"])
            pop.destroy()
            self.rm_thinking()
            self.msg("System", "Switched to Demo Mode")
        Button(pop, text="Reset to Demo Mode", font=("Consolas", 10), bg=self.C["red"], fg="white",
               bd=0, relief="flat", padx=14, pady=5, cursor="hand2", command=do_reset).pack(pady=8)
        Button(pop, text="Close", font=("Consolas", 10), bg=self.C["bgl"], fg=self.C["fg"],
               bd=0, relief="flat", padx=20, pady=5, command=pop.destroy).pack(pady=8)
def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
if __name__ == "__main__":
    main()
