#!/usr/bin/env python3
# TuringClaw - Stream Renderer (M3-1)
# 流式渲染 + 停止控制

import time
import threading
from tkinter import END


class StreamRenderer:
    """流式文本渲染器：每 chunk 立刻插入到 tkinter Text + 触发状态栏更新 + 节流
    
    使用:
        renderer = StreamRenderer(text_widget, statusbar)
        for chunk in stream:
            renderer.feed(chunk)
        renderer.finish()
    """

    def __init__(self, text_widget=None, statusbar=None, throttle_ms=50):
        """Args:
            text_widget: tkinter Text widget (或 None 用于纯逻辑测试)
            statusbar: 可选 StatusBar 实例
            throttle_ms: 状态栏更新节流(毫秒)
        """
        self.text = text_widget
        self.statusbar = statusbar
        self.throttle_ms = throttle_ms
        self._buffer = ""
        self._chunk_count = 0
        self._token_estimate = 0
        self._start_time = None
        self._last_status_update = 0
        self._stopped = False
        self._lock = threading.Lock()

    def feed(self, chunk: str):
        """接收一个文本 chunk"""
        if not chunk:
            return
        with self._lock:
            if self._stopped:
                return
            if self._start_time is None:
                self._start_time = time.time()
            self._buffer += chunk
            self._chunk_count += 1
            # 估算 token: 英文 ~4 字符/token, 中文 ~1.5 字符/token
            self._token_estimate += max(1, len(chunk) // 3)
        # 插入 UI (无锁 - tkinter 不支持跨线程)
        if self.text is not None:
            try:
                self.text.insert(END, chunk)
                self.text.see(END)
            except Exception:
                pass
        # 节流状态栏更新
        self._maybe_update_statusbar()

    def _maybe_update_statusbar(self):
        now = time.time() * 1000  # ms
        if self.statusbar is not None and (now - self._last_status_update) >= self.throttle_ms:
            self._last_status_update = now
            try:
                self.statusbar.update(out_tokens=self._token_estimate)
            except Exception:
                pass

    def stop(self):
        """停止接收后续 chunk"""
        with self._lock:
            self._stopped = True

    def finish(self):
        """完成流式: 最后一次状态栏更新"""
        if self.statusbar is not None:
            try:
                self.statusbar.update(out_tokens=self._token_estimate, finished=True)
            except Exception:
                pass

    def get_stats(self):
        """返回统计信息"""
        with self._lock:
            elapsed = 0.0
            if self._start_time:
                elapsed = time.time() - self._start_time
            return {
                "chunks": self._chunk_count,
                "tokens_est": self._token_estimate,
                "chars": len(self._buffer),
                "elapsed_s": round(elapsed, 2),
                "stopped": self._stopped,
            }
