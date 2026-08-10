"""
tool_usage_stats.py — 工具调用统计更新器

GSM V10 Layer 4 (Tacit) 组件
螺旋A（自我进化线）的一部分：记录每次工具调用的成功率、延迟、上下文和共现关系，
形成 Agent 对"什么时候用什么工具"的统计直觉。

数据文件：~/.TuringClaw/cognitive/layer4_tacit/tool_usage_stats.json

触发：每次工具调用后调用 on_tool_call()
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_stats() -> dict[str, Any]:
    """返回空统计骨架。"""
    return {
        "tools": {},
        "patterns": {
            "preferred_sequence": [],
            "avoid_when": {},
        },
        "meta": {
            "created": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "version": "1.0",
        },
    }


class ToolUsageStatsUpdater:
    """工具调用统计更新器。

    每次工具调用后调用 :meth:`on_tool_call`，自动维护：
    - 总调用数 / 成功数 / 成功率
    - 滚动平均延迟
    - 按上下文分类的统计
    - 工具共现关系（当前工具之后通常跟什么工具）

    Attributes:
        data_dir: 数据文件所在目录。
        file_path: ``tool_usage_stats.json`` 完整路径。
        _last_tool: 上一次调用的工具名（用于共现统计）。
    """

    def __init__(
        self,
        cognitive_dir: str | Path | None = None,
    ) -> None:
        """初始化更新器。

        Args:
            cognitive_dir: 认知层数据根目录。
                默认 ``~/.TuringClaw/cognitive``。
        """
        base = Path(cognitive_dir) if cognitive_dir else Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir: Path = base / "layer4_tacit"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path: Path = self.data_dir / "tool_usage_stats.json"
        self._last_tool: str | None = None

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """加载统计数据；文件不存在或损坏时返回空骨架。"""
        if not self.file_path.exists():
            return _default_stats()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # 基本校验
            if "tools" not in data:
                data = _default_stats() | data
            return data
        except (json.JSONDecodeError, OSError):
            return _default_stats()

    def save(self, data: dict[str, Any]) -> None:
        """持久化统计数据。"""
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self.file_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def on_tool_call(
        self,
        tool_name: str,
        context: str = "default",
        success: bool = True,
        latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        """记录一次工具调用。

        Args:
            tool_name: 工具名称，如 ``"web_search"``、``"read"``、``"exec"``。
            context: 调用上下文/场景标签，如 ``"technical_query"``。
            success: 是否成功。
            latency_ms: 调用耗时（毫秒）。

        Returns:
            更新后的完整统计字典。
        """
        data = self.load()
        tools = data["tools"]

        # 初始化工具条目
        if tool_name not in tools:
            tools[tool_name] = {
                "total_calls": 0,
                "success_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "contexts": {},
                "co_occurrence": {},
            }

        tool = tools[tool_name]
        tool["total_calls"] += 1
        if success:
            tool["success_count"] += 1
        tool["success_rate"] = round(tool["success_count"] / tool["total_calls"], 4)

        # 滚动平均延迟
        prev_avg = tool["avg_latency_ms"]
        n = tool["total_calls"]
        tool["avg_latency_ms"] = round(prev_avg + (latency_ms - prev_avg) / n, 2)

        # 上下文统计
        if "contexts" not in tool:
            tool["contexts"] = {}
        ctx = tool["contexts"].get(context, {"calls": 0, "success": 0, "rate": 0.0})
        ctx["calls"] += 1
        if success:
            ctx["success"] += 1
        ctx["rate"] = round(ctx["success"] / ctx["calls"], 4)
        tool["contexts"][context] = ctx

        # 共现：上一次工具 → 当前工具
        if self._last_tool is not None:
            if "co_occurrence" not in tools[self._last_tool]:
                tools[self._last_tool]["co_occurrence"] = {}
            co = tools[self._last_tool]["co_occurrence"]
            co[tool_name] = co.get(tool_name, 0) + 1
            # 归一化为比率
            total_co = sum(co.values())
            for k in co:
                co[k] = round(co[k] / total_co, 4) if total_co > 0 else 0.0

        self._last_tool = tool_name
        self.save(data)
        return data

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_tool_stats(self, tool_name: str) -> dict[str, Any] | None:
        """返回某个工具的统计；不存在返回 ``None``。"""
        data = self.load()
        return data["tools"].get(tool_name)

    def get_preferred_sequence(self) -> list[str]:
        """根据共现关系推断最常用的工具调用序列。"""
        data = self.load()
        tools = data["tools"]
        if not tools:
            return []

        # 找到最常作为起点的工具（被共现引用最多的）
        incoming: dict[str, int] = {}
        for name, t in tools.items():
            for target, ratio in t.get("co_occurrence", {}).items():
                incoming[target] = incoming.get(target, 0) + ratio

        # 起点 = 被引用最多但自己引用别人最多的（最早被调用的）
        start_candidates = set(tools.keys()) - (set(incoming.keys()) if incoming else set())
        if not start_candidates:
            start_candidates = {max(tools, key=lambda n: tools[n]["total_calls"])}

        sequence: list[str] = []
        visited: set[str] = set()
        current = start_candidates.pop()

        while current and current not in visited:
            sequence.append(current)
            visited.add(current)
            co = tools[current].get("co_occurrence", {})
            if not co:
                break
            current = max(co, key=co.get)  # type: ignore[arg-type]

        return sequence

    def add_avoid_rule(self, tool_name: str, reason: str) -> None:
        """添加"何时避免使用某工具"的规则。"""
        data = self.load()
        data["patterns"]["avoid_when"][tool_name] = reason
        self.save(data)

    # ------------------------------------------------------------------
    # 自测
    # ------------------------------------------------------------------

    @staticmethod
    def _self_test() -> None:
        """简单自测：模拟几次工具调用并打印结果。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            updater = ToolUsageStatsUpdater(cognitive_dir=td)

            # 模拟调用序列
            updater.on_tool_call("read", "config_check", success=True, latency_ms=50)
            updater.on_tool_call("exec", "build", success=True, latency_ms=3000)
            updater.on_tool_call("write", "output", success=True, latency_ms=100)
            updater.on_tool_call("read", "config_check", success=True, latency_ms=45)
            updater.on_tool_call("exec", "build", success=False, latency_ms=5000)

            stats = updater.load()
            assert stats["tools"]["read"]["total_calls"] == 2
            assert stats["tools"]["exec"]["total_calls"] == 2
            assert stats["tools"]["exec"]["success_count"] == 1
            assert stats["tools"]["write"]["total_calls"] == 1

            seq = updater.get_preferred_sequence()
            print(f"preferred_sequence: {seq}")
            print(f"exec stats: {json.dumps(stats['tools']['exec'], ensure_ascii=False, indent=2)}")
            print("✅ tool_usage_stats 自测通过")


if __name__ == "__main__":
    ToolUsageStatsUpdater._self_test()
