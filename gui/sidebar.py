#!/usr/bin/env python3
# TuringClaw - Session Sidebar (M3-5)
# 左侧会话列表 + 搜索 + 右键菜单 (重命名/删除/导出)

import os
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from tkinter import Frame, Label, Listbox, Entry, Button, StringVar, END
from tkinter import ttk, Menu


class SessionSidebar:
    """会话侧栏组件
    
    功能:
    - 列出 ~/.TuringClaw/chat_history/ 下的所有 session
    - 搜索框过滤
    - 右键菜单: 重命名/删除/导出
    - 双击加载
    - 新建会话按钮
    """
    COLORS = {
        "bg": "#1e1e2e",
        "bgl": "#313244",
        "fg": "#cdd6f4",
        "dim": "#a6adc8",
        "cyan": "#00d4ff",
        "red": "#f38ba8",
        "green": "#a6e3a1",
    }

    def __init__(self, parent, history_manager, on_select=None, on_new=None,
                 on_rename=None, on_delete=None, on_export=None):
        """
        Args:
            parent: 父 widget
            history_manager: ChatHistoryManager 实例
            on_select: 选择 session 回调 (file_path)
            on_new: 新建会话回调
            on_rename: 重命名回调 (file_path, new_name)
            on_delete: 删除回调 (file_path)
            on_export: 导出回调 (file_path)
        """
        self.parent = parent
        self.history = history_manager
        self.on_select = on_select
        self.on_new = on_new
        self.on_rename = on_rename
        self.on_delete = on_delete
        self.on_export = on_export
        self._all_sessions = []
        self._filter = ""
        self.frame = Frame(parent, bg=self.COLORS["bg"], width=220)
        self.frame.pack_propagate(False)
        self._build()

    def _build(self):
        C = self.COLORS
        # 标题
        title = Label(self.frame, text="会话", font=("Consolas", 11, "bold"),
                      bg=C["bg"], fg=C["cyan"])
        title.pack(fill="x", padx=8, pady=(8, 4))
        # 新建按钮
        new_btn = Button(self.frame, text="+ 新建", font=("Consolas", 10, "bold"),
                         bg=C["cyan"], fg="#1e1e2e", bd=0, relief="flat",
                         cursor="hand2", command=self._handle_new)
        new_btn.pack(fill="x", padx=8, pady=4)
        # 搜索框
        self.search_var = StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        self.search_entry = Entry(self.frame, textvariable=self.search_var,
                                  font=("Consolas", 10), bg=C["bgl"], fg=C["fg"],
                                  insertbackground=C["cyan"], bd=0, relief="flat")
        self.search_entry.pack(fill="x", padx=8, pady=4, ipady=4)
        # 列表
        list_frame = Frame(self.frame, bg=C["bg"])
        list_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.listbox = Listbox(list_frame, bg=C["bgl"], fg=C["fg"],
                               selectbackground=C["cyan"], selectforeground="#1e1e2e",
                               font=("Consolas", 9), bd=0, highlightthickness=0,
                               activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        # 事件
        self.listbox.bind("<Double-Button-1>", self._on_double_click)
        self.listbox.bind("<Button-3>", self._on_right_click)
        # 右键菜单 (懒创建)
        self._context_menu = None
        # 初始加载
        self.refresh()

    def refresh(self):
        """刷新列表"""
        self._all_sessions = self.history.list_sessions(limit=100)
        self._apply_filter()

    def _apply_filter(self):
        """应用搜索过滤"""
        self.listbox.delete(0, END)
        for s in self._all_sessions:
            display = self._format_session(s)
            if self._filter and self._filter.lower() not in display.lower():
                continue
            self.listbox.insert(END, display)
        # 保存原始 session 引用 (通过 _session_refs)
        if not hasattr(self, "_session_refs"):
            self._session_refs = []
        self._session_refs = [s for s in self._all_sessions
                              if not self._filter
                              or self._filter.lower() in self._format_session(s).lower()]

    def _format_session(self, s):
        """格式化 session 显示"""
        # 时间: 2026-06-27 19:00
        try:
            dt = datetime.fromisoformat(s.get("start_time", ""))
            time_str = dt.strftime("%m-%d %H:%M")
        except Exception:
            time_str = s.get("start_time", "")[:16]
        msg_count = s.get("message_count", 0)
        preview = s.get("preview", "")[:18].replace("\n", " ")
        return f"{time_str} ({msg_count}) {preview}"

    def _on_search_change(self, *args):
        self._filter = self.search_var.get()
        self._apply_filter()

    def _on_double_click(self, event=None):
        """双击加载"""
        idx = self.listbox.curselection()
        if not idx:
            return
        session = self._session_refs[idx[0]]
        if self.on_select:
            try:
                self.on_select(session["file"])
            except Exception as e:
                print(f"[WARN] on_select 失败: {e}")

    def _on_right_click(self, event=None):
        """右键弹出菜单"""
        idx = self.listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._session_refs):
            return
        self.listbox.selection_clear(0, END)
        self.listbox.selection_set(idx)
        if self._context_menu is None:
            self._context_menu = Menu(self.frame, tearoff=0,
                                       bg=self.COLORS["bgl"], fg=self.COLORS["fg"],
                                       activebackground=self.COLORS["cyan"],
                                       activeforeground="#1e1e2e")
            self._context_menu.add_command(label="加载", command=self._handle_select)
            self._context_menu.add_separator()
            self._context_menu.add_command(label="重命名", command=self._handle_rename)
            self._context_menu.add_command(label="删除", command=self._handle_delete)
            self._context_menu.add_separator()
            self._context_menu.add_command(label="导出 Markdown", command=lambda: self._handle_export("md"))
            self._context_menu.add_command(label="导出 JSON", command=lambda: self._handle_export("json"))
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _get_selected(self):
        idx = self.listbox.curselection()
        if not idx:
            return None
        return self._session_refs[idx[0]]

    def _handle_new(self):
        if self.on_new:
            try:
                self.on_new()
            except Exception as e:
                print(f"[WARN] on_new 失败: {e}")
        self.refresh()

    def _handle_select(self):
        s = self._get_selected()
        if s and self.on_select:
            try:
                self.on_select(s["file"])
            except Exception as e:
                print(f"[WARN] on_select 失败: {e}")

    def _handle_rename(self):
        s = self._get_selected()
        if not s:
            return
        from tkinter import simpledialog
        new_name = simpledialog.askstring("重命名会话", "新名称:", parent=self.frame)
        if not new_name:
            return
        if self.on_rename:
            try:
                self.on_rename(s["file"], new_name)
            except Exception as e:
                print(f"[WARN] on_rename 失败: {e}")
        self.refresh()

    def _handle_delete(self):
        s = self._get_selected()
        if not s:
            return
        from tkinter import messagebox
        if not messagebox.askyesno("确认删除", f"确定删除会话？\n{s.get('preview', '')[:30]}"):
            return
        if self.on_delete:
            try:
                self.on_delete(s["file"])
            except Exception as e:
                print(f"[WARN] on_delete 失败: {e}")
        else:
            # 默认直接删
            self.history.delete_session(s["file"])
        self.refresh()

    def _handle_export(self, fmt):
        s = self._get_selected()
        if not s:
            return
        from tkinter import filedialog
        ext = "md" if fmt == "md" else "json"
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{ext.upper()} 文件", f"*.{ext}"), ("所有文件", "*.*")],
            parent=self.frame,
        )
        if not path:
            return
        if self.on_export:
            try:
                self.on_export(s["file"], path, fmt)
            except Exception as e:
                print(f"[WARN] on_export 失败: {e}")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
