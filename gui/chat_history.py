#!/usr/bin/env python3
# TuringClaw - Chat History Manager
# 聊天记录持久化模块

import os
import json
import threading
from pathlib import Path
from datetime import datetime


class ChatHistoryManager:
    """聊天历史管理器，负责会话的创建、保存、加载、搜索和导出"""

    def __init__(self, history_dir=None):
        if history_dir is None:
            history_dir = Path.home() / ".TuringClaw" / "chat_history"
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._session = None
        self._session_file = None

    def start_session(self, provider=None, model=None):
        """开始新会话，创建会话记录"""
        with self._lock:
            # 如果有未关闭的会话，先保存
            if self._session is not None:
                self._save_session()

            now = datetime.now()
            session_id = now.strftime("%Y%m%d_%H%M%S")
            self._session = {
                "session_id": session_id,
                "start_time": now.isoformat(),
                "end_time": None,
                "messages": [],
                "model": model,
                "provider": provider,
                "message_count": 0
            }
            self._session_file = self.history_dir / f"chat_{session_id}.json"
            self._save_session()
            return session_id

    def add_message(self, role, content):
        """添加一条消息到当前会话（实时保存，防止崩溃丢数据）"""
        with self._lock:
            if self._session is None:
                return

            msg = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            self._session["messages"].append(msg)
            self._session["message_count"] = len(self._session["messages"])
            self._save_session()

    def end_session(self):
        """结束会话，保存到文件"""
        with self._lock:
            if self._session is None:
                return
            self._session["end_time"] = datetime.now().isoformat()
            self._save_session()
            self._session = None
            self._session_file = None

    def load_session(self, session_file):
        """加载指定会话文件"""
        session_path = Path(session_file)
        if not session_path.is_absolute():
            session_path = self.history_dir / session_path

        if not session_path.exists():
            return None

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Failed to load session {session_file}: {e}")
            return None

    def list_sessions(self, limit=20):
        """列出最近的会话（按时间倒序）"""
        sessions = []
        try:
            files = sorted(self.history_dir.glob("chat_*.json"), reverse=True)
        except OSError:
            return sessions

        for f in files[:limit]:
            summary = self.get_session_summary(f)
            if summary:
                sessions.append(summary)
        return sessions

    def get_session_summary(self, session_file):
        """获取会话摘要（用于显示在历史列表中）"""
        session_path = Path(session_file)
        if not session_path.is_absolute():
            session_path = self.history_dir / session_path

        if not session_path.exists():
            return None

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        start_time = data.get("start_time", "未知时间")
        # 取第一条用户消息作为预览
        preview = ""
        for msg in data.get("messages", []):
            if msg.get("role") == "user":
                preview = msg.get("content", "")[:50]
                break

        return {
            "file": str(session_path),
            "session_id": data.get("session_id", ""),
            "start_time": start_time,
            "end_time": data.get("end_time", ""),
            "model": data.get("model") or "未知",
            "provider": data.get("provider") or "未知",
            "message_count": data.get("message_count", 0),
            "preview": preview
        }

    def search_messages(self, keyword, limit=10):
        """搜索包含关键词的消息"""
        results = []
        keyword_lower = keyword.lower()

        try:
            files = sorted(self.history_dir.glob("chat_*.json"), reverse=True)
        except OSError:
            return results

        for f in files:
            if len(results) >= limit:
                break
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, IOError):
                continue

            for msg in data.get("messages", []):
                if len(results) >= limit:
                    break
                if keyword_lower in msg.get("content", "").lower():
                    results.append({
                        "session_id": data.get("session_id", ""),
                        "start_time": data.get("start_time", ""),
                        "model": data.get("model") or "未知",
                        "role": msg.get("role", ""),
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "file": str(f)
                    })
        return results

    def delete_session(self, session_file):
        """删除指定会话"""
        session_path = Path(session_file)
        if not session_path.is_absolute():
            session_path = self.history_dir / session_path

        try:
            if session_path.exists():
                session_path.unlink()
                return True
        except OSError as e:
            print(f"[WARN] Failed to delete session {session_file}: {e}")
        return False

    def export_session(self, session_file, export_path, format="txt"):
        """导出会话为 txt 或 markdown 格式"""
        data = self.load_session(session_file)
        if data is None:
            return False

        export_path = Path(export_path)

        try:
            if format == "markdown" or format == "md":
                lines = []
                lines.append(f"# 聊天记录 - {data.get('session_id', '')}")
                lines.append("")
                lines.append(f"- **时间**: {data.get('start_time', '')}")
                if data.get("end_time"):
                    lines.append(f"- **结束**: {data.get('end_time')}")
                lines.append(f"- **模型**: {data.get('model') or '未知'}")
                lines.append(f"- **提供商**: {data.get('provider') or '未知'}")
                lines.append(f"- **消息数**: {data.get('message_count', 0)}")
                lines.append("")
                lines.append("---")
                lines.append("")
                for msg in data.get("messages", []):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    ts = msg.get("timestamp", "")
                    role_display = {"user": "👤 用户", "assistant": "🤖 助手", "system": "⚙️ 系统"}.get(role, role)
                    lines.append(f"### {role_display}  `{ts}`")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")
                content_out = "\n".join(lines)
            else:
                # txt 格式
                lines = []
                lines.append(f"聊天记录 - {data.get('session_id', '')}")
                lines.append(f"时间: {data.get('start_time', '')}")
                if data.get("end_time"):
                    lines.append(f"结束: {data.get('end_time')}")
                lines.append(f"模型: {data.get('model') or '未知'}")
                lines.append(f"提供商: {data.get('provider') or '未知'}")
                lines.append(f"消息数: {data.get('message_count', 0)}")
                lines.append("=" * 60)
                lines.append("")
                for msg in data.get("messages", []):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    ts = msg.get("timestamp", "")
                    role_display = {"user": "用户", "assistant": "助手", "system": "系统"}.get(role, role)
                    lines.append(f"[{ts}] {role_display}:")
                    lines.append(content)
                    lines.append("-" * 40)
                content_out = "\n".join(lines)

            with open(export_path, "w", encoding="utf-8") as f:
                f.write(content_out)
            return True
        except IOError as e:
            print(f"[WARN] Failed to export session: {e}")
            return False

    def _save_session(self):
        """内部方法：保存当前会话到文件（调用者需持有锁）"""
        if self._session is None or self._session_file is None:
            return

        try:
            with open(self._session_file, "w", encoding="utf-8") as f:
                json.dump(self._session, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[WARN] Failed to save session: {e}")
