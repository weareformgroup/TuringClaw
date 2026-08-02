#!/usr/bin/env python3
# TuringClaw - StatusBar (M3-3)
# 底部状态栏: Provider | Model | Tokens | 延迟 | 健康状态

import time
import threading
from tkinter import Frame, Label


class StatusBar:
    """状态栏组件
    
    字段: ● health | provider | model | ↓ in | ↑ out | ⏱ latency
    """
    COLORS = {
        "green": "#a6e3a1",
        "yellow": "#f9e2af",
        "red": "#f38ba8",
        "dim": "#a6adc8",
        "bg": "#181825",
        "fg": "#cdd6f4",
        "cyan": "#00d4ff",
    }

    def __init__(self, parent, bg=None, fg=None):
        self.frame = Frame(parent, bg=bg or self.COLORS["bg"], height=24)
        self.frame.pack_propagate(False)
        self._lock = threading.Lock()
        self._data = {
            "provider": "未选择",
            "model": "未选择",
            "in_tokens": 0,
            "out_tokens": 0,
            "latency_ms": 0,
            "health": "dim",  # green/yellow/red/dim
            "streaming": False,
        }
        self._build_labels()

    def _build_labels(self):
        """构建状态栏标签"""
        bg = self.frame.cget("bg")
        fg = self.COLORS["fg"]
        # 健康指示器
        self.health_label = Label(self.frame, text="●", font=("Consolas", 12, "bold"),
                                  bg=bg, fg=self.COLORS["dim"], width=2)
        self.health_label.pack(side="left", padx=(8, 2))
        # Provider | Model
        self.provider_label = Label(self.frame, text="未选择", font=("Consolas", 10),
                                    bg=bg, fg=self.COLORS["cyan"], width=14, anchor="w")
        self.provider_label.pack(side="left", padx=4)
        self.model_label = Label(self.frame, text="未选择", font=("Consolas", 10),
                                 bg=bg, fg=fg, width=22, anchor="w")
        self.model_label.pack(side="left", padx=4)
        # Token 计数
        self.in_label = Label(self.frame, text="↓ 0", font=("Consolas", 10),
                              bg=bg, fg=self.COLORS["dim"], width=8, anchor="e")
        self.in_label.pack(side="left", padx=4)
        self.out_label = Label(self.frame, text="↑ 0", font=("Consolas", 10),
                               bg=bg, fg=self.COLORS["dim"], width=8, anchor="e")
        self.out_label.pack(side="left", padx=4)
        # 延迟
        self.latency_label = Label(self.frame, text="⏱ 0ms", font=("Consolas", 10),
                                   bg=bg, fg=self.COLORS["dim"], width=10, anchor="e")
        self.latency_label.pack(side="left", padx=4)
        # 流式状态
        self.stream_label = Label(self.frame, text="", font=("Consolas", 10),
                                  bg=bg, fg=self.COLORS["yellow"], width=8, anchor="w")
        self.stream_label.pack(side="left", padx=4)

    def update(self, **kwargs):
        """更新状态栏字段
        
        支持字段: provider, model, in_tokens, out_tokens, latency_ms, 
                 health, streaming, finished
        """
        with self._lock:
            for k, v in kwargs.items():
                if k == "finished":
                    self._data["streaming"] = False
                elif k in self._data:
                    self._data[k] = v
            self._refresh_ui()

    def _refresh_ui(self):
        d = self._data
        # 健康颜色
        color = {
            "green": self.COLORS["green"],
            "yellow": self.COLORS["yellow"],
            "red": self.COLORS["red"],
            "dim": self.COLORS["dim"],
        }.get(d["health"], self.COLORS["dim"])
        try:
            self.health_label.config(fg=color)
            # Provider/Model
            self.provider_label.config(text=d["provider"][:14])
            self.model_label.config(text=d["model"][:22])
            # Tokens
            self.in_label.config(text=f"↓ {d['in_tokens']}")
            self.out_label.config(text=f"↑ {d['out_tokens']}")
            # 延迟
            self.latency_label.config(text=f"⏱ {d['latency_ms']}ms")
            # 流式
            if d["streaming"]:
                self.stream_label.config(text="● 流式中", fg=self.COLORS["yellow"])
            else:
                self.stream_label.config(text="")
        except Exception:
            # 跨线程调用时安全忽略 (生产用 root.after 重试)
            pass

    def set_provider(self, name, model):
        """便捷方法: 设置 provider + model"""
        self.update(provider=name, model=model)

    def start_stream(self):
        """标记流式开始"""
        self.update(streaming=True)

    def end_stream(self):
        """标记流式结束"""
        self.update(streaming=False, finished=True)

    def get_data(self):
        with self._lock:
            return dict(self._data)


class MockTkParent:
    """mock frame (用于无 tkinter 环境的单元测试)"""
    def __init__(self):
        self.children = {}
    def pack(self, **kw): pass
    def pack_propagate(self, v): pass
    def cget(self, key): return "#181825"
