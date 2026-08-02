#!/usr/bin/env python3
# TuringClaw - Health Monitor (M3-7)
# Provider 健康检查 (可配置频率)

import time
import json
import threading
import urllib.request
from pathlib import Path


class HealthMonitor:
    """Provider 健康监控器
    
    频率可配置 (在 config.json 中):
    {
      "health": {
        "cloud_interval_s": 30,
        "local_interval_s": 60,
        "timeout_s": 5
      }
    }
    
    状态: green (< 1s) / yellow (1-3s) / red (> 3s 或失败)
    """
    DEFAULT_CONFIG = {
        "cloud_interval_s": 30,
        "local_interval_s": 60,
        "timeout_s": 5,
    }

    def __init__(self, config_path=None):
        self.config_path = Path(config_path) if config_path else None
        self.config = dict(self.DEFAULT_CONFIG)
        self._load_config()
        self._status = {}  # provider_name -> {status, latency_ms, last_check, error_count}
        self._stopped = False
        self._lock = threading.Lock()

    def _load_config(self):
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    full = json.load(f)
                health_cfg = full.get("health", {})
                for k, v in health_cfg.items():
                    if k in self.DEFAULT_CONFIG:
                        self.config[k] = v
            except (json.JSONDecodeError, IOError):
                pass

    def save_config(self, **overrides):
        """保存配置到 config.json"""
        if not self.config_path:
            return False
        for k, v in overrides.items():
            if k in self.DEFAULT_CONFIG:
                self.config[k] = v
        try:
            data = {}
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["health"] = self.config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] 保存 health config 失败: {e}")
            return False

    def check_provider(self, name, ping_fn, is_local=False):
        """检查单个 provider 健康状态
        
        Args:
            name: provider 名
            ping_fn: () -> None 同步函数, 不抛 = 成功
            is_local: 本地 (频率低)
        """
        start = time.time()
        error = None
        try:
            ping_fn()
        except Exception as e:
            error = str(e)
        latency = (time.time() - start) * 1000  # ms
        if error is not None:
            status = "red"
        elif latency < 1000:
            status = "green"
        elif latency < 3000:
            status = "yellow"
        else:
            status = "red"
        with self._lock:
            prev = self._status.get(name, {"error_count": 0})
            error_count = prev.get("error_count", 0)
            if error is not None:
                error_count += 1
            else:
                error_count = 0
            self._status[name] = {
                "status": status,
                "latency_ms": round(latency, 1),
                "last_check": time.time(),
                "error_count": error_count,
                "is_local": is_local,
                "error": error,
            }
        return self._status[name]

    def get_status(self, name=None):
        """获取状态 (name=None 全部)"""
        with self._lock:
            if name:
                return dict(self._status.get(name, {}))
            return {k: dict(v) for k, v in self._status.items()}

    def get_summary(self):
        """获取摘要 (用于状态栏)"""
        with self._lock:
            greens = sum(1 for v in self._status.values() if v["status"] == "green")
            yellows = sum(1 for v in self._status.values() if v["status"] == "yellow")
            reds = sum(1 for v in self._status.values() if v["status"] == "red")
            return {
                "total": len(self._status),
                "green": greens,
                "yellow": yellows,
                "red": reds,
            }

    def start_daemon(self, providers_to_check):
        """启动守护线程定期检查
        
        Args:
            providers_to_check: list of (name, ping_fn, is_local)
        """
        self._stopped = False
        t = threading.Thread(target=self._daemon_loop,
                              args=(providers_to_check,), daemon=True)
        t.start()
        return t

    def stop(self):
        self._stopped = True

    def _daemon_loop(self, providers):
        while not self._stopped:
            for name, ping_fn, is_local in providers:
                if self._stopped:
                    return
                self.check_provider(name, ping_fn, is_local)
            # 按各 provider 频率不同 sleep (取最短)
            min_interval = min(
                self.config["local_interval_s"] if is_local else self.config["cloud_interval_s"]
                for _, _, is_local in providers
            )
            # 实际上为了简化, 我们用 5s 轮询, 内部判断是否到时间
            for _ in range(5):
                if self._stopped:
                    return
                time.sleep(1)

    def should_check(self, name):
        """根据频率判断是否该检查"""
        with self._lock:
            st = self._status.get(name)
            if not st:
                return True
            elapsed = time.time() - st.get("last_check", 0)
            interval = self.config["local_interval_s"] if st.get("is_local") else self.config["cloud_interval_s"]
            return elapsed >= interval

    def get_config(self):
        return dict(self.config)


# 便捷 ping 函数
def ping_http(url, timeout=None):
    """HTTP GET ping"""
    timeout = timeout or 5
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read(1024)  # 读一点就够
