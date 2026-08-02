"""
tacit_distillation.py — 隐性知识蒸馏器

GSM V10 螺旋B（外部校准线）组件
从用户行为中推断未明说的隐性原则，蒸馏为 Agent 可执行的直觉。

数据文件：
    - ~/.TuringClaw/cognitive/calibration/tacit_distillation.json
    - 联动写入 ~/.TuringClaw/cognitive/layer4_tacit/execution_intuition.json

蒸馏流程：
    1. 观察用户操作
    2. 识别行为模式（非偶发、重复出现）
    3. 推断隐含原则（用户这样做是因为相信什么）
    4. 写入 tacit_distillation.json + execution_intuition.json
    5. 后续任务中应用此原则
    6. 观察效果 → confidence 调整
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _default_store() -> dict[str, Any]:
    return {
        "observations": [],
        "distillation_rule": (
            "观察用户行为模式 → 推断隐含原则 → "
            "写入execution_intuition → 验证是否改善后续行为"
        ),
        "meta": {
            "created": _utc_now_iso(),
            "last_updated": _utc_now_iso(),
            "version": "1.0",
        },
    }


DISTILLATION_TRIGGERS: list[dict[str, Any]] = [
    {"trigger": "user_proactive_action", "meaning": "用户主动做了未被要求的事", "min_confidence": 0.5},
    {"trigger": "user_rejection_with_alternative", "meaning": "用户拒绝了Agent的建议用了不同方法", "min_confidence": 0.6},
    {"trigger": "repeated_pattern", "threshold": 3, "meaning": "这是习惯不是偶然", "min_confidence": 0.7},
    {"trigger": "priority_statement", "meaning": "用户的价值排序", "min_confidence": 0.8},
]


class TacitDistiller:
    """隐性知识蒸馏器。

    从用户行为模式推断隐含原则，写入蒸馏记录和执行直觉。

    工作原理：
        1. on_user_behavior() — 观察用户行为
        2. 识别是否匹配蒸馏触发条件
        3. infer_principle() — 推断隐含原则
        4. distill() — 写入蒸馏记录 + 直觉层
        5. validate_distillation() — 后续验证调整 confidence
    """

    def __init__(self, cognitive_dir: str | Path | None = None) -> None:
        base = Path(cognitive_dir) if cognitive_dir else Path.home() / ".TuringClaw" / "cognitive"
        self.cognitive_dir: Path = base
        self.data_dir: Path = base / "calibration"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path: Path = self.data_dir / "tacit_distillation.json"
        self._intuition_path: Path = base / "layer4_tacit" / "execution_intuition.json"
        self._intuition_dir: Path = base / "layer4_tacit"
        self._intuition_dir.mkdir(parents=True, exist_ok=True)
        self._behavior_counts: dict[str, int] = {}

    def load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return _default_store()
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "observations" not in data:
                data = _default_store() | data
            return data
        except (json.JSONDecodeError, OSError):
            return _default_store()

    def save(self, data: dict[str, Any]) -> None:
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self.file_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.file_path)

    def _load_intuitions(self) -> dict[str, Any]:
        if not self._intuition_path.exists():
            return {"intuitions": [], "update_rule": "", "meta": {}}
        try:
            with self._intuition_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"intuitions": [], "update_rule": "", "meta": {}}

    def _save_intuitions(self, data: dict[str, Any]) -> None:
        data.setdefault("meta", {})["last_updated"] = _utc_now_iso()
        tmp = self._intuition_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(self._intuition_path)

    def on_user_behavior(
        self,
        behavior: str,
        context: str = "",
        trigger_type: str = "user_proactive_action",
    ) -> dict[str, Any] | None:
        """观察用户行为，判断是否触发蒸馏。"""
        behavior_key = behavior.lower().strip()
        self._behavior_counts[behavior_key] = self._behavior_counts.get(behavior_key, 0) + 1
        repeat_count = self._behavior_counts[behavior_key]

        triggered = False
        min_confidence = 0.5

        for trig in DISTILLATION_TRIGGERS:
            if trig["trigger"] == trigger_type:
                if trigger_type == "repeated_pattern":
                    threshold = trig.get("threshold", 3)
                    if repeat_count >= threshold:
                        triggered = True
                        min_confidence = trig["min_confidence"]
                else:
                    triggered = True
                    min_confidence = trig["min_confidence"]
                break

        if not triggered:
            return None

        principle = self.infer_principle(behavior, context)
        if not principle:
            return None

        return self.distill(behavior, principle, context, trigger_type, min_confidence)

    def infer_principle(self, behavior: str, context: str) -> dict[str, str] | None:
        """从用户行为推断隐含原则。当前为规则匹配，后续可替换为LLM。"""
        rules: list[dict[str, Any]] = [
            {"keywords": ["反复推敲", "再检查", "验证"],
             "principle": "验证比执行更重要",
             "trigger": "用户说'检查一下'",
             "action": "先全量扫描再逐项验证，不凭记忆"},
            {"keywords": ["先做维护", "维护好才", "基础设施", "先处理"],
             "principle": "基础设施优先——工具不靠谱时不要开始上层工作",
             "trigger": "任务开始前",
             "action": "先检查基础设施状态，确认工具可靠后再开始核心工作"},
            {"keywords": ["重启后", "没生效", "还是不行"],
             "principle": "配置变更必须验证端到端效果",
             "trigger": "配置变更后",
             "action": "重启后验证实际效果，不只是文件层面"},
            {"keywords": ["不要", "换成", "改用"],
             "principle": "用户有偏好的实现路径",
             "trigger": "方案选择时",
             "action": "记录用户偏好，后续同类任务优先使用该方法"},
            {"keywords": ["优先", "先做这个", "important"],
             "principle": "用户有明确的价值排序",
             "trigger": "任务排序时",
             "action": "按用户优先级排序，不自行决定顺序"},
        ]

        combined = (behavior + " " + context).lower()
        for rule in rules:
            for kw in rule["keywords"]:
                if kw.lower() in combined:
                    return {"trigger": rule["trigger"], "action": rule["action"], "principle": rule["principle"]}
        return None

    def distill(
        self,
        behavior: str,
        inferred_principle: dict[str, str],
        context: str = "",
        trigger_type: str = "user_proactive_action",
        initial_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """执行蒸馏：写入蒸馏记录 + 执行直觉层。"""
        data = self.load()
        obs_id = self._next_obs_id(data["observations"])
        intuition_id = self._next_intuition_id()

        obs = {
            "id": obs_id,
            "timestamp": _utc_now_iso(),
            "observed_human": "用户",
            "behavior": behavior,
            "context": context,
            "trigger_type": trigger_type,
            "inferred_principle": inferred_principle["principle"],
            "distilled_to": intuition_id,
            "confidence": initial_confidence,
            "validation_count": 0,
            "status": "internalizing",
        }
        data["observations"].append(obs)
        self.save(data)

        # 同时写入直觉层
        intuitions = self._load_intuitions()
        intuitions.setdefault("intuitions", []).append({
            "id": intuition_id,
            "trigger": inferred_principle["trigger"],
            "learned_action": inferred_principle["action"],
            "evidence_count": 1,
            "evidence": [{"date": _today(), "failure": f"从用户行为蒸馏：{behavior}"}],
            "confidence": initial_confidence,
            "status": "internalizing",
            "source": "distillation",
            "source_obs_id": obs_id,
        })
        self._save_intuitions(intuitions)
        return obs

    def validate_distillation(self, obs_id: str, user_satisfied: bool) -> dict[str, Any] | None:
        """验证蒸馏出的原则在后续使用中是否有效。

        - 用户满意 → confidence += 0.1
        - 用户不满意 → confidence -= 0.2
        - confidence > 0.8 且 validation_count >= 3 → internalized
        - confidence < 0.2 → deprecated
        """
        data = self.load()
        target = None
        for obs in data["observations"]:
            if obs["id"] == obs_id:
                target = obs
                break
        if target is None:
            return None

        target["validation_count"] += 1
        if user_satisfied:
            target["confidence"] = min(0.99, round(target["confidence"] + 0.1, 2))
        else:
            target["confidence"] = max(0.0, round(target["confidence"] - 0.2, 2))

        if target["confidence"] >= 0.8 and target["validation_count"] >= 3:
            target["status"] = "internalized"
        elif target["confidence"] < 0.2:
            target["status"] = "deprecated"

        self.save(data)
        self._sync_intuition_validation(target["distilled_to"], user_satisfied)
        return target

    def get_observations(self) -> list[dict[str, Any]]:
        return self.load()["observations"]

    def get_internalized(self) -> list[dict[str, Any]]:
        return [o for o in self.load()["observations"] if o.get("status") == "internalized"]

    def get_active(self) -> list[dict[str, Any]]:
        return [o for o in self.load()["observations"] if o.get("status") != "deprecated"]

    def _sync_intuition_validation(self, intuition_id: str, user_satisfied: bool) -> None:
        intuitions = self._load_intuitions()
        for it in intuitions.get("intuitions", []):
            if it["id"] == intuition_id:
                if user_satisfied:
                    it["confidence"] = min(0.99, round(it.get("confidence", 0.5) + 0.1, 2))
                else:
                    it["confidence"] = max(0.0, round(it.get("confidence", 0.5) - 0.2, 2))
                if it["confidence"] >= 0.8 and it.get("evidence_count", 0) >= 3:
                    it["status"] = "internalized"
                elif it["confidence"] < 0.2:
                    it["status"] = "deprecated"
                self._save_intuitions(intuitions)
                return

    def _next_obs_id(self, observations: list[dict[str, Any]]) -> str:
        max_num = 0
        for o in observations:
            try:
                num = int(o["id"].replace("obs_", ""))
                max_num = max(max_num, num)
            except (ValueError, KeyError):
                pass
        return f"obs_{max_num + 1:03d}"

    def _next_intuition_id(self) -> str:
        intuitions = self._load_intuitions()
        max_num = 0
        for it in intuitions.get("intuitions", []):
            try:
                num = int(it["id"].replace("intuition_", ""))
                max_num = max(max_num, num)
            except (ValueError, KeyError):
                pass
        return f"intuition_{max_num + 1:03d}"

    @staticmethod
    def _self_test() -> None:
        """简单自测。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            distiller = TacitDistiller(cognitive_dir=td)

            # 测试原则推断
            principle = distiller.infer_principle("用户要求反复推敲", "Agent声称完成但实际未完成")
            assert principle is not None
            assert "验证" in principle["principle"]

            # 蒸馏一条
            obs = distiller.distill(
                behavior="用户要求'反复推敲'",
                inferred_principle=principle,
                context="Agent声称完成但实际未完成",
                trigger_type="user_proactive_action",
                initial_confidence=0.5,
            )
            assert obs["id"] == "obs_001"
            assert obs["status"] == "internalizing"

            # 验证直觉层联动
            intuitions = distiller._load_intuitions()
            assert len(intuitions["intuitions"]) == 1
            assert intuitions["intuitions"][0]["source"] == "distillation"

            # 验证蒸馏——满意
            for _ in range(3):
                distiller.validate_distillation("obs_001", user_satisfied=True)

            obs_updated = distiller.get_observations()[0]
            assert obs_updated["status"] == "internalized"
            assert obs_updated["confidence"] > 0.8

            # 验证直觉层同步
            intuitions = distiller._load_intuitions()
            it = intuitions["intuitions"][0]
            assert it["status"] == "internalized"

            # 测试 on_user_behavior 自动流程
            result = distiller.on_user_behavior(
                behavior="先做维护再做GSM",
                context="GSM是核心工作",
                trigger_type="priority_statement",
            )
            assert result is not None
            assert "基础设施" in result["inferred_principle"]

            # 测试 repeated_pattern（需要 3 次才触发）
            for i in range(2):
                r = distiller.on_user_behavior(
                    behavior="用 .NET 写入文件",
                    context="write工具截断",
                    trigger_type="repeated_pattern",
                )
                assert r is None

            r3 = distiller.on_user_behavior(
                behavior="用 .NET 写入文件",
                context="write工具截断",
                trigger_type="repeated_pattern",
            )
            assert r3 is not None

            all_obs = distiller.get_observations()
            print(f"total observations: {len(all_obs)}")
            print(f"internalized: {len(distiller.get_internalized())}")
            for o in all_obs:
                print(f"  {o['id']}: {o['inferred_principle']} (conf={o['confidence']}, status={o['status']})")
            print("[OK] tacit_distillation self-test passed")


if __name__ == "__main__":
    TacitDistiller._self_test()
