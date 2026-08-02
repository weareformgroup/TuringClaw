#!/usr/bin/env python3
# TuringClaw - KeyBindings (M3-4)
# 快捷键绑定辅助

# 快捷键清单 + 默认行为
KEY_BINDINGS = {
    "<Control-Return>": {
        "action": "send_message",
        "description": "发送消息",
        "scope": "input_focus",
    },
    "<Control-l>": {
        "action": "clear_input",
        "description": "清空输入框",
        "scope": "global",
    },
    "<Escape>": {
        "action": "stop_stream",
        "description": "停止流式响应",
        "scope": "global",
    },
    "<Control-t>": {
        "action": "toggle_tab",
        "description": "切换 对话/编程 Tab",
        "scope": "global",
    },
    "<Control-Shift-s>": {
        "action": "toggle_sidebar",
        "description": "显示/隐藏会话侧栏",
        "scope": "global",
    },
    "<Control-comma>": {
        "action": "open_settings",
        "description": "打开设置",
        "scope": "global",
    },
}


def bind_default_keys(root, app):
    """绑定所有默认快捷键到 root
    
    Args:
        root: tk.Tk() 实例
        app: TuringClaw App 实例 (需有 _on_send, _on_stop, inp, notebook 等)
    """
    def on_ctrl_return(e):
        # 仅在输入框聚焦时触发
        if hasattr(app, "inp") and root.focus_get() is app.inp:
            if hasattr(app, "_on_send"):
                app._on_send()
            return "break"
        return None

    def on_ctrl_l(e):
        if hasattr(app, "inp"):
            app.inp.delete(0, "end")
        return "break"

    def on_escape(e):
        # 仅在有流式进行中时触发
        if hasattr(app, "_is_streaming") and app._is_streaming:
            if hasattr(app, "_on_stop"):
                app._on_stop()
            return "break"
        return None

    def on_ctrl_t(e):
        if hasattr(app, "notebook"):
            try:
                current = app.notebook.index(app.notebook.select())
                total = len(app.notebook.tabs())
                if total > 0:
                    app.notebook.select((current + 1) % total)
                    if hasattr(app, "_on_tab_changed"):
                        app._on_tab_changed()
            except Exception:
                pass
        return "break"

    def on_ctrl_shift_s(e):
        if hasattr(app, "_toggle_sidebar"):
            app._toggle_sidebar()
        return "break"

    def on_ctrl_comma(e):
        if hasattr(app, "show_settings"):
            try:
                app.show_settings()
            except Exception:
                pass
        return "break"

    root.bind_all("<Control-Return>", on_ctrl_return)
    root.bind_all("<Control-l>", on_ctrl_l)
    root.bind_all("<Escape>", on_escape)
    root.bind_all("<Control-t>", on_ctrl_t)
    root.bind_all("<Control-Shift-s>", on_ctrl_shift_s)
    root.bind_all("<Control-comma>", on_ctrl_comma)

    return [
        "<Control-Return>",
        "<Control-l>",
        "<Escape>",
        "<Control-t>",
        "<Control-Shift-s>",
        "<Control-comma>",
    ]
