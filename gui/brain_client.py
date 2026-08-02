"""
BrainClient — GBrain HTTP API 客户端

让 TuringClaw 的 AgentLoop 能够：
1. 查询 GBrain 知识库（brain-ops 协议）
2. 写入信号到 GBrain（signal-detector 协议）
3. 获取 brain 健康状态

通过 HTTP API 与 GBrain 微服务通信（gbrain serve --http --port 8484）。
"""

import json
import urllib.request
import urllib.error
from typing import Optional
from threading import Lock


class BrainClient:
    """GBrain HTTP API 客户端，线程安全。"""

    def __init__(
        self,
        base_url: str = "http://localhost:8484",
        token: str = "gbrain_94a387f3530308d92a11150f429dd3aa9bc0a4ccad4ed2ae107d2247c0b2ea58",
        agent_id: str = "turingclaw",
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.timeout = timeout
        self._lock = Lock()
        self._available: Optional[bool] = None

    def _mcp_call(self, method: str, params: dict) -> Optional[dict]:
        """通过 MCP JSON-RPC 协议调用 GBrain。"""
        url = f"{self.base_url}/mcp"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        # 先 initialize（如果需要 session）
        # 实际上 gbrain HTTP 支持无状态调用，直接 tools/call
        if method == "tools/list":
            body = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }).encode()
        else:
            body = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": method,
                    "arguments": params,
                },
            }).encode()

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                # SSE 格式: "event: message\ndata: {...}\n\n"
                for line in raw.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            content = data["result"].get("content", [])
                            if content and isinstance(content, list):
                                text = content[0].get("text", "")
                                try:
                                    return json.loads(text)
                                except (json.JSONDecodeError, ValueError):
                                    return {"raw": text}
                        return data.get("result")
        except urllib.error.URLError as e:
            self._available = False
            return None
        except Exception as e:
            self._available = False
            return None

    def is_available(self) -> bool:
        """检查 GBrain 服务是否可用。"""
        if self._available is not None:
            return self._available
        try:
            url = f"{self.base_url}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._available = data.get("status") == "ok"
                return self._available
        except Exception:
            self._available = False
            return False

    def search(self, query: str, limit: int = 5) -> list:
        """关键词搜索 brain pages。"""
        result = self._mcp_call("search", {"query": query, "limit": limit})
        if isinstance(result, list):
            return result
        return []

    def query(self, question: str, limit: int = 5) -> list:
        """混合语义搜索（向量 + FTS）。"""
        result = self._mcp_call("query", {"question": question, "limit": limit})
        if isinstance(result, list):
            return result
        return []

    def get_page(self, slug: str) -> Optional[dict]:
        """读取完整 brain page。"""
        result = self._mcp_call("get", {"slug": slug})
        if isinstance(result, dict):
            return result
        return None

    def put_page(self, slug: str, body: str, page_type: str = "note") -> Optional[dict]:
        """写入或更新 brain page。"""
        result = self._mcp_call("put", {
            "slug": slug,
            "body": body,
            "type": page_type,
        })
        return result

    def add_timeline(self, slug: str, date: str, title: str, body: str = "") -> bool:
        """添加时间线条目。"""
        result = self._mcp_call("timeline-add", {
            "slug": slug,
            "date": date,
            "title": title,
            "body": body,
        })
        return result is not None

    def list_pages(self, page_type: str = "all") -> list:
        """列出 brain pages。"""
        result = self._mcp_call("list", {"type": page_type})
        if isinstance(result, list):
            return result
        return []

    def get_stats(self) -> Optional[dict]:
        """获取 brain 统计信息。"""
        result = self._mcp_call("stats", {})
        if isinstance(result, dict):
            return result
        return None

    def build_context_knowledge(self, user_message: str) -> str:
        """
        为 ContextBuilder 生成 brain 知识注入文本。
        如果 brain 不可用或无结果，返回空字符串。
        """
        if not self.is_available():
            return ""

        with self._lock:
            # 1. 先关键词搜索（更可靠，不依赖 embedding）
            results = self.search(user_message, limit=3)
            if not results:
                # 2. fallback 语义搜索
                results = self.query(user_message, limit=3)
            if not results:
                return ""

        # 构建注入文本
        lines = ["[Brain Knowledge]"]
        for r in results[:3]:
            title = r.get("title", "Untitled")
            slug = r.get("slug", "")
            chunk = r.get("chunk_text", "")
            score = r.get("score", 0)
            # 截断过长的 chunk，移除可能导致编码问题的字符
            if len(chunk) > 500:
                chunk = chunk[:500] + "..."
            # 替换可能导致编码问题的 emoji 字符
            chunk = chunk.replace("\u2705", "[OK]").replace("\u23f3", "[...]")
            lines.append("- [" + title + "] (" + slug + ", score=" + str(round(score, 2)) + "): " + chunk)

        return "\n".join(lines)

    def capture_signal(self, user_message: str, assistant_response: str = "") -> bool:
        """
        信号捕获（简化版 signal-detector）。
        从用户消息中提取实体/想法，写入 brain。
        """
        if not self.is_available():
            return False

        # 简化的实体检测：检测项目名/技术名
        entities = self._extract_entities(user_message)
        for entity_type, entity_name, slug in entities:
            try:
                self.put_page(
                    slug=slug,
                    body=f"# {entity_name}\n\n[Source: TuringClaw, {self._today()}]\n\nMentioned in conversation.",
                    page_type=entity_type,
                )
            except Exception:
                pass

        return len(entities) > 0

    def _extract_entities(self, text: str) -> list:
        """从文本中提取实体（简化版）。"""
        entities = []
        text_lower = text.lower()

        # 已知项目名
        known_projects = {
            "turingclaw": ("project", "TuringClaw", "projects/turingclaw"),
            "gsm": ("concept", "GSM (Goal State Machine)", "concepts/gsm"),
            "gbrain": ("concept", "GBrain", "concepts/gbrain"),
            "ollama": ("concept", "Ollama", "concepts/ollama"),
            "codex": ("concept", "Codex CLI", "concepts/codex-cli"),
        }

        for keyword, (etype, name, slug) in known_projects.items():
            if keyword in text_lower:
                entities.append((etype, name, slug))

        return entities

    @staticmethod
    def _today() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")


# 全局单例
_brain_client: Optional[BrainClient] = None
_brain_lock = Lock()


def get_brain_client() -> BrainClient:
    """获取全局 BrainClient 单例。"""
    global _brain_client
    if _brain_client is None:
        with _brain_lock:
            if _brain_client is None:
                _brain_client = BrainClient()
    return _brain_client
