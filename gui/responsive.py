#!/usr/bin/env python3
# TuringClaw - Responsive Layout (M3-9)
# 窗口尺寸断点自适应

# 断点定义 (宽 x 高)
BREAKPOINTS = {
    "compact": (0, 600),       # 移动/极窄
    "narrow": (600, 800),      # 窄 (默认)
    "normal": (800, 700),      # 正常
    "wide": (1200, 800),       # 宽屏
}


def detect_layout(width, height):
    """根据窗口尺寸选择布局模式
    
    Returns: dict with {sidebar, statusbar, font, padding, ...}
    """
    if width < 600:
        return {
            "name": "compact",
            "show_sidebar": False,
            "show_statusbar": True,
            "font_size": 10,
            "padding": 4,
            "tab_height": 28,
        }
    elif width < 800:
        return {
            "name": "narrow",
            "show_sidebar": True,  # 紧凑
            "sidebar_width": 180,
            "show_statusbar": True,
            "font_size": 11,
            "padding": 6,
            "tab_height": 30,
        }
    elif width < 1200:
        return {
            "name": "normal",
            "show_sidebar": True,
            "sidebar_width": 220,
            "show_statusbar": True,
            "font_size": 12,
            "padding": 8,
            "tab_height": 32,
        }
    else:
        return {
            "name": "wide",
            "show_sidebar": True,
            "sidebar_width": 260,
            "show_statusbar": True,
            "font_size": 13,
            "padding": 10,
            "tab_height": 36,
        }


class ResponsiveMixin:
    """为 App 类提供响应式能力的 Mixin
    
    用法:
    class App(ResponsiveMixin, ...):
        def __init__(...):
            ...
            self.bind_responsive()
    """
    RESPONSIVE_THRESHOLD_W = 50  # 触发 on_resize 的最小宽度变化 (像素)

    def bind_responsive(self):
        """绑定窗口缩放事件"""
        if hasattr(self, "root"):
            self.root.bind("<Configure>", self._on_configure)
            self._last_w = 0
            self._last_h = 0
            self._current_layout = None

    def _on_configure(self, event=None):
        """窗口尺寸变化回调"""
        if event and event.widget is not getattr(self, "root", None):
            return
        root = getattr(self, "root", None)
        if not root:
            return
        try:
            w = root.winfo_width()
            h = root.winfo_height()
        except Exception:
            return
        if abs(w - self._last_w) < self.RESPONSIVE_THRESHOLD_W and abs(h - self._last_h) < self.RESPONSIVE_THRESHOLD_W:
            return
        self._last_w = w
        self._last_h = h
        layout = detect_layout(w, h)
        if layout["name"] != (self._current_layout or {}).get("name"):
            self._current_layout = layout
            self.apply_layout(layout)

    def apply_layout(self, layout):
        """应用布局 (子类可重写)"""
        if hasattr(self, "statusbar") and hasattr(self.statusbar, "frame"):
            try:
                if layout["show_statusbar"]:
                    self.statusbar.frame.pack(fill="x", side="bottom", padx=layout["padding"])
                else:
                    self.statusbar.frame.pack_forget()
            except Exception:
                pass
        if hasattr(self, "statusbar") and hasattr(self.statusbar, "set_font_size"):
            try:
                self.statusbar.set_font_size(layout["font_size"])
            except Exception:
                pass
