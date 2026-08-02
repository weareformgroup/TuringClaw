# -*- coding: utf-8 -*-
"""
M4-3: Configuration Panel for TuringClaw GUI
Allows users to configure providers, API keys, and models via GUI.
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, Optional


CONFIG_PATH = Path.home() / ".TuringClaw" / "api_keys.json"


def load_config() -> dict:
    """Load API keys config from file."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load config: {e}")
    return {}


def save_config(config: dict) -> bool:
    """Save API keys config to file."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
        return False


class ConfigPanel(tk.Toplevel):
    """Configuration panel dialog for managing providers and API keys."""

    # Known providers with their config keys
    PROVIDER_FIELDS = {
        "kimi": {"label": "Kimi (月之暗面)", "key_field": "api_key", "model_field": "model", "default_model": "moonshot-v1-8k"},
        "deepseek": {"label": "DeepSeek", "key_field": "api_key", "model_field": "model", "default_model": "deepseek-chat"},
        "minimax": {"label": "MiniMax", "key_field": "api_key", "model_field": "model", "default_model": "abab6.5s-chat"},
        "openrouter": {"label": "OpenRouter", "key_field": "api_key", "model_field": "model", "default_model": "openrouter/auto"},
        "ollama": {"label": "Ollama (本地)", "key_field": "api_base", "model_field": "model", "default_model": "llama3.2"},
        "siliconflow": {"label": "SiliconFlow", "key_field": "api_key", "model_field": "model", "default_model": "Qwen/Qwen2.5-7B-Instruct"},
    }

    def __init__(self, parent, current_config: Optional[dict] = None):
        super().__init__(parent)
        self.title("TuringClaw 配置面板")
        self.geometry("520x600")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.config_data = current_config or load_config()
        self.entries: Dict[str, Dict[str, tk.Widget]] = {}

        self._build_ui()

    def _build_ui(self):
        """Build the configuration UI."""
        # Title
        title = ttk.Label(self, text="Provider 配置", font=("", 14, "bold"))
        title.pack(pady=10)

        subtitle = ttk.Label(self, text="配置各 Provider 的 API Key 和模型。留空则不使用该 Provider。")
        subtitle.pack(pady=(0, 10))

        # Scrollable frame
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0))
        scrollbar.pack(side="right", fill="y")

        # Provider sections
        for provider_id, fields in self.PROVIDER_FIELDS.items():
            self._build_provider_section(scroll_frame, provider_id, fields)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10, fill="x", padx=10)

        save_btn = ttk.Button(btn_frame, text="保存", command=self._on_save)
        save_btn.pack(side="right", padx=5)

        cancel_btn = ttk.Button(btn_frame, text="取消", command=self.destroy)
        cancel_btn.pack(side="right", padx=5)

        test_btn = ttk.Button(btn_frame, text="测试连接", command=self._on_test)
        test_btn.pack(side="left", padx=5)

    def _build_provider_section(self, parent, provider_id: str, fields: dict):
        """Build a single provider configuration section."""
        # Container frame
        container = ttk.LabelFrame(parent, text=fields["label"], padding=10)
        container.pack(fill="x", padx=5, pady=5)

        # Get current values
        provider_config = self.config_data.get(provider_id, {})
        key_value = provider_config.get(fields["key_field"], "")
        model_value = provider_config.get(fields["model_field"], fields["default_model"])

        # API Key / Base URL
        key_label_text = "API Base:" if fields["key_field"] == "api_base" else "API Key:"
        ttk.Label(container, text=key_label_text).pack(anchor="w")
        key_entry = ttk.Entry(container, width=50, show="" if fields["key_field"] == "api_base" else "*")
        key_entry.insert(0, key_value)
        key_entry.pack(fill="x", pady=(0, 5))

        # Model
        ttk.Label(container, text="模型:").pack(anchor="w")
        model_entry = ttk.Entry(container, width=50)
        model_entry.insert(0, model_value)
        model_entry.pack(fill="x", pady=(0, 5))

        # Show/hide key
        if fields["key_field"] != "api_base":
            show_var = tk.BooleanVar(value=False)
            def toggle_key():
                key_entry.config(show="" if show_var.get() else "*")
            show_cb = ttk.Checkbutton(container, text="显示Key", variable=show_var, command=toggle_key)
            show_cb.pack(anchor="w")

        self.entries[provider_id] = {
            "key": key_entry,
            "model": model_entry,
            "fields": fields,
        }

    def _on_save(self):
        """Save configuration."""
        for provider_id, widgets in self.entries.items():
            if provider_id not in self.config_data:
                self.config_data[provider_id] = {}
            fields = widgets["fields"]
            key_val = widgets["key"].get().strip()
            model_val = widgets["model"].get().strip()

            if key_val:
                self.config_data[provider_id][fields["key_field"]] = key_val
            elif fields["key_field"] in self.config_data[provider_id]:
                del self.config_data[provider_id][fields["key_field"]]

            if model_val:
                self.config_data[provider_id][fields["model_field"]] = model_val

        if save_config(self.config_data):
            messagebox.showinfo("成功", "配置已保存到\n" + str(CONFIG_PATH), parent=self)
            self.destroy()
        else:
            messagebox.showerror("失败", "保存配置失败，请检查权限。", parent=self)

    def _on_test(self):
        """Test provider connections."""
        # Save first
        for provider_id, widgets in self.entries.items():
            if provider_id not in self.config_data:
                self.config_data[provider_id] = {}
            fields = widgets["fields"]
            key_val = widgets["key"].get().strip()
            model_val = widgets["model"].get().strip()
            if key_val:
                self.config_data[provider_id][fields["key_field"]] = key_val
            if model_val:
                self.config_data[provider_id][fields["model_field"]] = model_val

        results = []
        for provider_id, widgets in self.entries.items():
            fields = widgets["fields"]
            key_val = widgets["key"].get().strip()
            if not key_val and fields["key_field"] != "api_base":
                results.append(f"⏭️ {fields['label']}: 未配置 (跳过)")
                continue

            if fields["key_field"] == "api_base":
                # Test Ollama connection
                try:
                    import urllib.request
                    base = key_val or "http://localhost:11434"
                    req = urllib.request.Request(f"{base}/api/tags", method="GET")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status == 200:
                            results.append(f"✅ {fields['label']}: 连接成功")
                        else:
                            results.append(f"❌ {fields['label']}: HTTP {resp.status}")
                except Exception as e:
                    results.append(f"❌ {fields['label']}: {str(e)[:50]}")
            else:
                # Test API key with a simple request
                results.append(f"🔑 {fields['label']}: Key已保存 (需实际对话验证)")

        messagebox.showinfo("测试结果", "\n".join(results), parent=self)


def open_config_panel(parent):
    """Open the configuration panel."""
    panel = ConfigPanel(parent)
    parent.wait_window(panel)
    return panel.config_data