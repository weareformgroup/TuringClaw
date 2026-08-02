"""
prompt_patterns.py — Prompt 模式效果记录

GSM V10 Layer 4 (Tacit) 组件
记录不同 Prompt 模式（回答结构、语气、详略度）的使用效果，
通过用户后续行为（追问次数、是否满意）推断哪种模式更好。

数据文件：~/.TuringClaw/cognitive/layer4_tacit/prompt_patterns.json

触发：每次 assistant 回复后调用 record_usage()
效果推断：用户后续无追问 = 满意；追问多 = 不满意
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_patterns() -> dict[str, Any]:
    return {
        "patterns": [],
        "statistical_tendency": {
            "best_pattern": None,
            "confidence": 0.0,
            "reason": "数据不足",
        },
        "meta": {
            "created": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "version": "1.0",
        },
    }


class PromptPatternsRecorder:
    """Prompt 模式效果记录器。

    记录每种回答模式的使用次数、用户满意度（以追问次数反推），
    并统计出最优模式。

    满意度推断规则：
        - ``avg_followup_questions < 1.0`` → 高满意度 (~0.9)
        - ``avg_followup_questions 1.0–2.0`` → 中等满意度 (~0.65)
        - ``avg_followup_questions > 2.0`` → 低满意度 (~0.4)

    使用流程：
        1. 回复前：调用 :meth:`register_pattern` 注册模式
        2. 回复后：调用 :meth:`record_usage` 记录使用
        3. 用户反应后：调用 :meth:`update_followup` 补充追问信息
        4. 调用 :meth:`recompute_tendency` 更新统计倾向
    """

    def __init__(
        self,
        cognitive_dir: str | Path | None = None,
    ) -> None:
        base = Path(cognitive_dir) if cognitive_dir else Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir: Path = base / "layer4_tacit"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path: Path = self.data_dir / "prompt_patterns.json"

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """加载模式数据；文件不存在或损坏时返回空骨架。"""
        if not self.file_path.exists():
            return _default_patterns()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "patterns" not in data:
                data = _default_patterns() | data
            return data
        except (json.JSONDecodeError, OSError):
            return _default_patterns()

    def save(self, data: dict[str, Any]) -> None:
        """持久化模式数据。"""
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self.file_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        description: str,
        template: str,
        pattern_id: str | None = None,
    ) -> str:
        """注册一个新的 Prompt 模式。

        如果 description 已存在则更新模板，不重复创建。

        Args:
            description: 模式描述，如 ``"先给结论再展开解释"``。
            template: 模式模板，如 ``"结论。以下是推理过程：..."``。
            pattern_id: 可选的自定义 ID。

        Returns:
            模式的 ID。
        """
        data = self.load()

        # 检查是否已有相同描述
        for p in data["patterns"]:
            if p["description"] == description:
                p["template"] = template
                self.save(data)
                return p["id"]

        pid = pattern_id or self._next_id(data["patterns"])
        data["patterns"].append(
            {
                "id": pid,
                "description": description,
                "template": template,
                "usage_count": 0,
                "user_satisfaction": 0.0,
                "avg_followup_questions": 0.0,
                "total_followup_questions": 0,
                "last_used": None,
            }
        )
        self.save(data)
        return pid

    def record_usage(
        self,
        pattern_id: str,
        followup_questions: int = 0,
    ) -> dict[str, Any] | None:
        """记录一次模式使用。

        Args:
            pattern_id: 模式 ID。
            followup_questions: 用户后续追问次数（0 表示满意）。

        Returns:
            更新后的模式条目，找不到返回 ``None``。
        """
        data = self.load()
        target = None
        for p in data["patterns"]:
            if p["id"] == pattern_id:
                target = p
                break

        if target is None:
            return None

        target["usage_count"] += 1
        target["total_followup_questions"] = (
            target.get("total_followup_questions", 0) + followup_questions
        )
        target["avg_followup_questions"] = round(
            target["total_followup_questions"] / target["usage_count"], 2
        )
        target["user_satisfaction"] = self._infer_satisfaction(
            target["avg_followup_questions"]
        )
        target["last_used"] = _utc_now_iso()

        self.save(data)
        self.recompute_tendency()
        return target

    def update_followup(
        self,
        pattern_id: str,
        additional_followup: int,
    ) -> dict[str, Any] | None:
        """补充记录用户在之后的追问次数（异步更新）。

        有时候追问不会立即发生，此方法允许后续补充。

        Args:
            pattern_id: 模式 ID。
            additional_followup: 额外的追问次数。

        Returns:
            更新后的模式条目。
        """
        data = self.load()
        target = None
        for p in data["patterns"]:
            if p["id"] == pattern_id:
                target = p
                break

        if target is None:
            return None

        target["total_followup_questions"] = (
            target.get("total_followup_questions", 0) + additional_followup
        )
        target["avg_followup_questions"] = round(
            target["total_followup_questions"] / max(target["usage_count"], 1), 2
        )
        target["user_satisfaction"] = self._infer_satisfaction(
            target["avg_followup_questions"]
        )

        self.save(data)
        self.recompute_tendency()
        return target

    def recompute_tendency(self) -> dict[str, Any]:
        """重新计算统计倾向，选出最优模式。

        Returns:
            更新后的 ``statistical_tendency`` 字典。
        """
        data = self.load()
        patterns = data["patterns"]

        if not patterns:
            data["statistical_tendency"] = {
                "best_pattern": None,
                "confidence": 0.0,
                "reason": "数据不足",
            }
            self.save(data)
            return data["statistical_tendency"]

        # 只看使用次数 >= 3 的模式
        qualified = [p for p in patterns if p["usage_count"] >= 3]

        if not qualified:
            data["statistical_tendency"] = {
                "best_pattern": None,
                "confidence": 0.0,
                "reason": "使用次数不足，无法判断",
            }
            self.save(data)
            return data["statistical_tendency"]

        best = max(qualified, key=lambda p: p["user_satisfaction"])
        confidence = min(0.99, best["user_satisfaction"])

        data["statistical_tendency"] = {
            "best_pattern": best["id"],
            "best_description": best["description"],
            "confidence": round(confidence, 2),
            "reason": f"满意度 {best['user_satisfaction']:.0%}，"
            f"平均追问 {best['avg_followup_questions']:.1f} 次",
        }
        self.save(data)
        return data["statistical_tendency"]

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_best_pattern(self) -> dict[str, Any] | None:
        """返回当前最优模式的信息。"""
        data = self.load()
        tendency = data.get("statistical_tendency", {})
        if not tendency.get("best_pattern"):
            return None
        for p in data["patterns"]:
            if p["id"] == tendency["best_pattern"]:
                return {**p, "tendency": tendency}
        return None

    def get_all_patterns(self) -> list[dict[str, Any]]:
        """返回所有模式。"""
        return self.load()["patterns"]

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _infer_satisfaction(self, avg_followup: float) -> float:
        """根据平均追问次数推断满意度。"""
        if avg_followup < 1.0:
            return 0.89
        elif avg_followup <= 2.0:
            return 0.65
        else:
            return 0.40

    def _next_id(self, patterns: list[dict[str, Any]]) -> str:
        """生成下一个模式 ID。"""
        max_num = 0
        for p in patterns:
            try:
                num = int(p["id"].replace("pattern_", ""))
                max_num = max(max_num, num)
            except (ValueError, KeyError):
                pass
        return f"pattern_{max_num + 1:03d}"

    # ------------------------------------------------------------------
    # 自测
    # ------------------------------------------------------------------

    @staticmethod
    def _self_test() -> None:
        """简单自测。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            rec = PromptPatternsRecorder(cognitive_dir=td)

            # 注册两个模式
            pid1 = rec.register_pattern("先给结论再展开解释", "结论。以下是推理过程：...")
            pid2 = rec.register_pattern("先分析再总结", "分析过程...。总结：...")

            # 模拟使用
            # pattern_001: 多次使用，少追问 → 高满意度
            for _ in range(5):
                rec.record_usage(pid1, followup_questions=0)
            rec.record_usage(pid1, followup_questions=1)

            # pattern_002: 多次使用，多追问 → 低满意度
            for _ in range(4):
                rec.record_usage(pid2, followup_questions=2)
            rec.record_usage(pid2, followup_questions=3)

            best = rec.get_best_pattern()
            assert best is not None
            assert best["id"] == pid1
            assert best["user_satisfaction"] > 0.65

            tendency = rec.load()["statistical_tendency"]
            assert tendency["best_pattern"] == pid1

            print(f"best pattern: {best['description']}")
            print(f"tendency: {json.dumps(tendency, ensure_ascii=False, indent=2)}")
            print("✅ prompt_patterns 自测通过")


if __name__ == "__main__":
    PromptPatternsRecorder._self_test()
