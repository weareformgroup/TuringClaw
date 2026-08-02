"""
execution_intuition.py — 执行直觉更新器

GSM V10 Layer 4 (Tacit) 组件
螺旋A（自我进化线）的核心：从失败中学习"直觉"——在什么场景下应该怎么做。

数据文件：~/.TuringClaw/cognitive/layer4_tacit/execution_intuition.json

触发：
    - 每次失败+反思 → on_failure()
    - 螺旋B隐性知识蒸馏 → on_distillation()
    - 成功使用已有直觉 → on_success reinforcement

更新规则：
    - 每次失败后自动创建/更新 intuition
    - confidence 随证据增加而上升
    - 连续 3 次成功使用后 status 升为 internalized
    - confidence < 0.2 时标记为 deprecated
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Sequence


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _default_intuitions() -> dict[str, Any]:
    return {
        "intuitions": [],
        "update_rule": (
            "每次失败后自动创建/更新intuition；"
            "连续3次成功使用后status升为internalized"
        ),
        "meta": {
            "created": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "version": "1.0",
        },
    }


class ExecutionIntuitionUpdater:
    """执行直觉更新器。

    从失败事件和隐性知识蒸馏中学习"直觉"——
    在特定触发条件下应该采取什么行动的统计性倾向。

    每条直觉包含：
    - ``trigger``: 触发条件（什么场景下激活）
    - ``learned_action``: 学到的行动方案
    - ``evidence``: 支持此直觉的证据列表
    - ``confidence``: 置信度 [0, 1]
    - ``status``: ``internalizing`` → ``internalized`` / ``deprecated``
    """

    def __init__(
        self,
        cognitive_dir: str | Path | None = None,
    ) -> None:
        base = Path(cognitive_dir) if cognitive_dir else Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir: Path = base / "layer4_tacit"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path: Path = self.data_dir / "execution_intuition.json"

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """加载直觉数据；文件不存在或损坏时返回空骨架。"""
        if not self.file_path.exists():
            return _default_intuitions()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "intuitions" not in data:
                data = _default_intuitions() | data
            return data
        except (json.JSONDecodeError, OSError):
            return _default_intuitions()

    def save(self, data: dict[str, Any]) -> None:
        """持久化直觉数据。"""
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self.file_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def on_failure(
        self,
        trigger: str,
        learned_action: str,
        failure_description: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """记录一次失败事件，创建或增强对应的直觉。

        Args:
            trigger: 触发条件描述，如 ``"用户说'检查一下'"``。
            learned_action: 从失败中学到的行动方案。
            failure_description: 失败的具体描述。
            date: 事件日期 (YYYY-MM-DD)，默认今天。

        Returns:
            被创建或更新的直觉条目。
        """
        data = self.load()
        date_str = date or _today()

        # 查找已有匹配直觉
        match = self._find_matching(data["intuitions"], trigger)

        if match:
            match["evidence_count"] += 1
            match["evidence"].append({"date": date_str, "failure": failure_description})
            match["confidence"] = min(0.99, round(match["confidence"] + 0.1, 2))

            # 3 次证据后升级
            if match["evidence_count"] >= 3 and match["status"] == "internalizing":
                match["status"] = "internalized"

            match["learned_action"] = learned_action
        else:
            match = {
                "id": self._next_id(data["intuitions"]),
                "trigger": trigger,
                "learned_action": learned_action,
                "evidence_count": 1,
                "evidence": [{"date": date_str, "failure": failure_description}],
                "confidence": 0.5,
                "status": "internalizing",
                "source": "failure",
            }
            data["intuitions"].append(match)

        self.save(data)
        return match

    def on_distillation(
        self,
        trigger: str,
        learned_action: str,
        source_description: str,
        date: str | None = None,
    ) -> dict[str, Any]:
        """从隐性知识蒸馏创建直觉（螺旋B触发）。

        与 :meth:`on_failure` 类似，但来源标记为 ``distillation``，
        初始 confidence 较低 (0.5)，需要后续验证。

        Args:
            trigger: 触发条件。
            learned_action: 蒸馏出的行动方案。
            source_description: 蒸馏来源描述（用户行为）。
            date: 事件日期。

        Returns:
            新创建的直觉条目。
        """
        data = self.load()
        date_str = date or _today()

        match = self._find_matching(data["intuitions"], trigger)
        if match:
            match["evidence_count"] += 1
            match["evidence"].append(
                {"date": date_str, "failure": f"从用户行为蒸馏：{source_description}"}
            )
            match["confidence"] = min(0.99, round(match["confidence"] + 0.05, 2))
        else:
            match = {
                "id": self._next_id(data["intuitions"]),
                "trigger": trigger,
                "learned_action": learned_action,
                "evidence_count": 1,
                "evidence": [
                    {"date": date_str, "failure": f"从用户行为蒸馏：{source_description}"}
                ],
                "confidence": 0.5,
                "status": "internalizing",
                "source": "distillation",
            }
            data["intuitions"].append(match)

        self.save(data)
        return match

    def on_success_reinforcement(
        self,
        intuition_id: str,
    ) -> dict[str, Any] | None:
        """记录一次成功使用某直觉的事件，增强其 confidence。

        连续 3 次成功使用后，status 从 ``internalizing`` 升为 ``internalized``。

        Args:
            intuition_id: 直觉 ID。

        Returns:
            更新后的直觉条目，找不到返回 ``None``。
        """
        data = self.load()
        target = None
        for it in data["intuitions"]:
            if it["id"] == intuition_id:
                target = it
                break

        if target is None:
            return None

        # 记录成功使用
        success_count = target.get("_success_count", 0) + 1
        target["_success_count"] = success_count

        # confidence 提升
        target["confidence"] = min(0.99, round(target["confidence"] + 0.05, 2))

        # 连续 3 次成功 → internalized
        if success_count >= 3 and target["status"] == "internalizing":
            target["status"] = "internalized"

        self.save(data)
        return target

    def on_rejection(
        self,
        intuition_id: str,
    ) -> dict[str, Any] | None:
        """某直觉被外部校准拒绝，降低 confidence。

        confidence < 0.2 时标记为 ``deprecated``。

        Args:
            intuition_id: 直觉 ID。

        Returns:
            更新后的直觉条目，找不到返回 ``None``。
        """
        data = self.load()
        target = None
        for it in data["intuitions"]:
            if it["id"] == intuition_id:
                target = it
                break

        if target is None:
            return None

        target["confidence"] = max(0.0, round(target["confidence"] - 0.2, 2))
        if target["confidence"] < 0.2:
            target["status"] = "deprecated"

        self.save(data)
        return target

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_by_trigger(self, trigger: str) -> list[dict[str, Any]]:
        """返回所有匹配某触发条件的直觉。"""
        data = self.load()
        return [it for it in data["intuitions"] if trigger.lower() in it["trigger"].lower()]

    def get_internalized(self) -> list[dict[str, Any]]:
        """返回所有已内化的直觉。"""
        data = self.load()
        return [it for it in data["intuitions"] if it["status"] == "internalized"]

    def get_active(self) -> list[dict[str, Any]]:
        """返回所有非 deprecated 的直觉。"""
        data = self.load()
        return [it for it in data["intuitions"] if it["status"] != "deprecated"]

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _find_matching(
        self,
        intuitions: list[dict[str, Any]],
        trigger: str,
    ) -> dict[str, Any] | None:
        """查找与 trigger 语义相似的已有直觉。

        当前实现为简单的关键词包含匹配。
        后续可替换为嵌入相似度。
        """
        trigger_lower = trigger.lower()
        for it in intuitions:
            existing = it["trigger"].lower()
            # 双向包含
            if trigger_lower in existing or existing in trigger_lower:
                return it
        return None

    def _next_id(self, intuitions: list[dict[str, Any]]) -> str:
        """生成下一个直觉 ID。"""
        max_num = 0
        for it in intuitions:
            try:
                num = int(it["id"].replace("intuition_", ""))
                max_num = max(max_num, num)
            except (ValueError, KeyError):
                pass
        return f"intuition_{max_num + 1:03d}"

    # ------------------------------------------------------------------
    # 自测
    # ------------------------------------------------------------------

    @staticmethod
    def _self_test() -> None:
        """简单自测。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            updater = ExecutionIntuitionUpdater(cognitive_dir=td)

            # 模拟 3 次失败 → 应 internalize
            for i in range(3):
                updater.on_failure(
                    trigger="用户说'检查一下'",
                    learned_action="先全量扫描再逐项验证，不凭记忆",
                    failure_description=f"第{i+1}次：凭记忆遗漏",
                )

            data = updater.load()
            it = data["intuitions"][0]
            assert it["evidence_count"] == 3
            assert it["status"] == "internalized"
            assert it["confidence"] >= 0.7

            # 模拟蒸馏
            updater.on_distillation(
                trigger="任务切换时",
                learned_action="执行收尾检查",
                source_description="用户多次在切换前要求清理",
            )
            data = updater.load()
            assert len(data["intuitions"]) == 2

            # 模拟成功强化
            iid = data["intuitions"][1]["id"]
            for _ in range(3):
                updater.on_success_reinforcement(iid)
            data = updater.load()
            assert data["intuitions"][1]["status"] == "internalized"

            # 模拟拒绝
            updater.on_rejection(data["intuitions"][0]["id"])
            data = updater.load()
            assert data["intuitions"][0]["confidence"] < 0.99

            print(f"intuitions count: {len(data['intuitions'])}")
            print(f"internalized: {len(updater.get_internalized())}")
            print("✅ execution_intuition 自测通过")


if __name__ == "__main__":
    ExecutionIntuitionUpdater._self_test()
