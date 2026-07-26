# -*- coding: utf-8 -*-
"""
QClawClient — OpenAI 兼容的流式 HTTP 客户端（纯标准库，无第三方依赖）。

用于 TuringClaw GUI 调用 QClaw 桥接的云端/本地模型（MiniMax / Ollama OpenAI 端点）。
支持 SSE 流式输出（on_chunk 回调）和非流式（on_complete 回调）。
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Callable, List, Dict, Optional


class QClawClient:
    """Minimal OpenAI-compatible streaming client."""

    def __init__(self, api_key: str = "", api_base: str = "http://localhost:11434/v1"):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        on_chunk: Callable[[str], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ):
        url = self.api_base + "/chat/completions"
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "text/event-stream")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                buf = ""
                content_parts = []
                while True:
                    chunk = resp.read(1)
                    if not chunk:
                        break
                    buf += chunk.decode("utf-8", errors="replace")
                    if "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                            if "choices" in obj and obj["choices"]:
                                delta = obj["choices"][0].get("delta", {})
                                piece = delta.get("content", "")
                                if piece:
                                    content_parts.append(piece)
                                    on_chunk(piece)
                        except json.JSONDecodeError:
                            continue
                on_done()
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = str(e)
            on_error(f"HTTP {e.code}: {err_body[:200]}")
        except Exception as e:
            on_error(str(e))

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """非流式调用，返回完整文本。"""
        url = self.api_base + "/chat/completions"
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "choices" in data and data["choices"]:
                    return data["choices"][0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[QClawClient] chat error: {e}")
        return None
