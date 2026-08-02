#!/usr/bin/env python3
# TuringClaw - Config Watcher (M3-8)
# 监听 config.json 改动, 3s 内自动重载

import time
import threading
from pathlib import Path


class ConfigWatcher:
    """配置文件监听器
    
    每 3s 检查 mtime, 变化时触发 on_change 回调
    """
    DEFAULT_INTERVAL_S = 3

    def __init__(self, config_path, on_change=None, interval_s=None):
        self.config_path = Path(config_path)
        self.on_change = on_change
        self.interval_s = interval_s or self.DEFAULT_INTERVAL_S
        self._last_mtime = self._safe_mtime()
        self._stopped = False
        self._thread = None
        self._error_count = 0

    def _safe_mtime(self):
        """安全获取 mtime (文件不存在返 0)"""
        try:
            if self.config_path.exists():
                return self.config_path.stat().st_mtime
        except OSError:
            pass
        return 0

    def start(self):
        """启动守护线程"""
        if self._thread and self._thread.is_alive():
            return False
        self._stopped = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stopped = True

    def _loop(self):
        while not self._stopped:
            time.sleep(self.interval_s)
            try:
                mtime = self._safe_mtime()
                if mtime != self._last_mtime and mtime > 0:
                    self._last_mtime = mtime
                    self._error_count = 0
                    if self.on_change:
                        try:
                            self.on_change()
                        except Exception as e:
                            print(f"[WARN] ConfigWatcher on_change 失败: {e}")
            except Exception as e:
                self._error_count += 1
                if self._error_count <= 3:
                    print(f"[WARN] ConfigWatcher 循环异常: {e}")

    def check_once(self):
        """手动检查一次 (用于测试)"""
        mtime = self._safe_mtime()
        if mtime != self._last_mtime and mtime > 0:
            self._last_mtime = mtime
            if self.on_change:
                self.on_change()
            return True
        return False

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()
