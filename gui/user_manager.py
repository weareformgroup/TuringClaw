#!/usr/bin/env python3
# TuringClaw - User Manager (M3-6)
# 本地多用户 + 4 位 PIN 保护 + 隔离历史/配置/API key

import os
import json
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from datetime import datetime


class UserManager:
    """本地多用户管理
    
    目录结构:
    ~/.TuringClaw/
    ├── users/
    │   ├── default/
    │   │   ├── pin.json (PIN hash, default 用户无 PIN)
    │   │   ├── api_keys.json
    │   │   ├── config.json
    │   │   └── chat_history/
    │   ├── alice/  (PIN: 1234)
    │   │   ├── pin.json
    │   │   └── ...
    
    兼容老路径: 首次启动时把 ~/.TuringClaw/api_keys.json 迁移到 users/default/
    """
    PIN_LENGTH = 4
    SALT_BYTES = 16
    PBKDF2_ITERATIONS = 100_000

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = Path.home() / ".TuringClaw"
        self.base_dir = Path(base_dir)
        self.users_dir = self.base_dir / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self._current_user = None
        self._lock = threading.Lock()
        self._migrate_legacy()

    def _migrate_legacy(self):
        """迁移老路径到 users/default/"""
        default_dir = self.users_dir / "default"
        if not default_dir.exists():
            default_dir.mkdir(parents=True, exist_ok=True)
            # 迁移 api_keys.json
            legacy_keys = self.base_dir / "api_keys.json"
            if legacy_keys.exists():
                target = default_dir / "api_keys.json"
                if not target.exists():
                    legacy_keys.rename(target)
            # 迁移 config.json (但保留 last_mode)
            legacy_config = self.base_dir / "config.json"
            if legacy_config.exists():
                target = default_dir / "config.json"
                if not target.exists():
                    legacy_config.rename(target)
            # 迁移 chat_history
            legacy_history = self.base_dir / "chat_history"
            if legacy_history.exists() and legacy_history.is_dir():
                target = default_dir / "chat_history"
                if not target.exists():
                    legacy_history.rename(target)
        # 初始化 default 用户的 pin.json (无 PIN)
        default_pin = self.users_dir / "default" / "pin.json"
        if not default_pin.exists():
            self._save_pin_data("default", {"has_pin": False})

    # ========== 用户 CRUD ==========
    def list_users(self):
        """列出所有用户"""
        users = []
        for d in sorted(self.users_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                pin_data = self._load_pin_data(d.name)
                users.append({
                    "name": d.name,
                    "has_pin": pin_data.get("has_pin", False),
                    "current": d.name == self._current_user,
                })
        return users

    def user_exists(self, username):
        """用户是否存在"""
        if not self._is_valid_username(username):
            return False
        return (self.users_dir / username).is_dir()

    def create_user(self, username, pin=None):
        """创建用户 (pin 可选)"""
        with self._lock:
            if not self._is_valid_username(username):
                raise ValueError(f"无效用户名: {username}")
            if self.user_exists(username):
                raise ValueError(f"用户已存在: {username}")
            user_dir = self.users_dir / username
            user_dir.mkdir(parents=True, exist_ok=True)
            (user_dir / "chat_history").mkdir(exist_ok=True)
            if pin:
                if len(pin) != self.PIN_LENGTH or not pin.isdigit():
                    raise ValueError(f"PIN 必须是 {self.PIN_LENGTH} 位数字")
                self._save_pin_data(username, self._hash_pin(pin))
            else:
                self._save_pin_data(username, {"has_pin": False})
            return True

    def delete_user(self, username):
        """删除用户 (default 不可删)"""
        with self._lock:
            if username == "default":
                raise ValueError("default 用户不可删除")
            if not self.user_exists(username):
                return False
            import shutil
            shutil.rmtree(self.users_dir / username, ignore_errors=True)
            if self._current_user == username:
                self._current_user = None
            return True

    def set_pin(self, username, pin):
        """设置/修改 PIN"""
        with self._lock:
            if not self.user_exists(username):
                raise ValueError(f"用户不存在: {username}")
            if len(pin) != self.PIN_LENGTH or not pin.isdigit():
                raise ValueError(f"PIN 必须是 {self.PIN_LENGTH} 位数字")
            self._save_pin_data(username, self._hash_pin(pin))
            return True

    def remove_pin(self, username):
        """移除 PIN (恢复无密码访问)"""
        with self._lock:
            if username == "default":
                return True
            if not self.user_exists(username):
                raise ValueError(f"用户不存在: {username}")
            self._save_pin_data(username, {"has_pin": False})
            return True

    # ========== 认证 ==========
    def switch_user(self, username, pin=None):
        """切换用户 (无 PIN 直接切, 有 PIN 必须验证)"""
        with self._lock:
            if not self.user_exists(username):
                raise ValueError(f"用户不存在: {username}")
            pin_data = self._load_pin_data(username)
            if pin_data.get("has_pin", False):
                if not pin:
                    raise PermissionError(f"用户 {username} 需要 PIN")
                if not self._verify_pin(pin, pin_data):
                    raise PermissionError("PIN 错误")
            self._current_user = username
            return True

    def get_current_user(self):
        """获取当前用户"""
        return self._current_user

    def require_user(self, username=None):
        """确保已登录指定用户 (无 PIN 直接, 有 PIN 弹窗)"""
        target = username or "default"
        if self._current_user == target:
            return True
        return self.switch_user(target)

    # ========== 路径 ==========
    def get_user_dir(self, username=None):
        """获取用户目录 (需先 switch_user)"""
        u = username or self._current_user
        if not u:
            raise ValueError("未选择用户")
        return self.users_dir / u

    def get_api_keys_path(self, username=None):
        return self.get_user_dir(username) / "api_keys.json"

    def get_config_path(self, username=None):
        return self.get_user_dir(username) / "config.json"

    def get_history_dir(self, username=None):
        return self.get_user_dir(username) / "chat_history"

    # ========== 内部 ==========
    @staticmethod
    def _is_valid_username(name):
        """合法用户名: 字母数字下划线, 1-32 字符"""
        if not name or not isinstance(name, str):
            return False
        if len(name) > 32 or len(name) < 1:
            return False
        return all(c.isalnum() or c in "_-" for c in name)

    def _hash_pin(self, pin):
        """PBKDF2 哈希 PIN"""
        salt = secrets.token_bytes(self.SALT_BYTES)
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"),
                                  salt, self.PBKDF2_ITERATIONS)
        return {
            "has_pin": True,
            "salt": salt.hex(),
            "hash": dk.hex(),
            "iterations": self.PBKDF2_ITERATIONS,
        }

    def _verify_pin(self, pin, pin_data):
        """验证 PIN"""
        if not pin_data.get("has_pin"):
            return True
        salt = bytes.fromhex(pin_data["salt"])
        expected = pin_data["hash"]
        iterations = pin_data.get("iterations", self.PBKDF2_ITERATIONS)
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"),
                                  salt, iterations)
        return hmac.compare_digest(dk.hex(), expected)

    def _pin_path(self, username):
        return self.users_dir / username / "pin.json"

    def _save_pin_data(self, username, data):
        path = self._pin_path(username)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_pin_data(self, username):
        path = self._pin_path(username)
        if not path.exists():
            return {"has_pin": False}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"has_pin": False}
