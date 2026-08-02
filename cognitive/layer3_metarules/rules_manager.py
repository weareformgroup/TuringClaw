# -*- coding: utf-8 -*-
"""
Layer 3: Meta-Rules — Meta-cognitive rule manager

GSM V10 B2: 四层结晶机制中的元认知层。
管理"什么时候该打破规则"的规则。

规则由 Layer 4 统计发现模式后自动创建草稿，需人类审批后生效。

数据结构 (meta_rules.json):
{
  "rules": [
    {
      "id": "rule_001",
      "trigger_pattern": "git_push_failure",
      "rule_text": "Git 命令必须用 C:\\Program Files\\Git\\cmd\\git.exe 全路径",
      "source": "tacit",          // tacit(自动发现) / mentor(导师反馈) / manual
      "status": "approved",        // draft / approved / rejected / deprecated
      "confidence": 0.9,
      "effectiveness": 0.0,        // 生效后验证的效果
      "applied_count": 0,          // 被应用次数
      "success_after": 0,          // 应用后成功次数
      "created_at": "2026-07-24T...",
      "approved_at": "2026-07-24T...",
      "evidence_trigger": "intu_003"  // 来源的 Layer 4 intuition ID
    }
  ],
  "version": 1
}
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class MetaRulesManager:
    """元认知规则管理器。"""

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            data_dir = Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "meta_rules.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"rules": [], "version": 1}

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def create_draft(
        self,
        trigger_pattern: str,
        rule_text: str,
        source: str = "tacit",
        evidence_trigger: str = "",
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """创建规则草稿（需审批后生效）。"""
        rule_id = self._next_id()
        now = datetime.now(timezone.utc).isoformat()
        rule = {
            "id": rule_id,
            "trigger_pattern": trigger_pattern,
            "rule_text": rule_text,
            "source": source,
            "status": "draft",
            "confidence": confidence,
            "effectiveness": 0.0,
            "applied_count": 0,
            "success_after": 0,
            "created_at": now,
            "approved_at": None,
            "evidence_trigger": evidence_trigger,
        }
        self._data["rules"].append(rule)
        self._save()
        return rule

    def approve(self, rule_id: str) -> Optional[dict[str, Any]]:
        """审批通过规则草稿。"""
        rule = self._find(rule_id)
        if rule and rule["status"] == "draft":
            rule["status"] = "approved"
            rule["approved_at"] = datetime.now(timezone.utc).isoformat()
            rule["confidence"] = min(1.0, rule["confidence"] + 0.2)
            self._save()
            return rule
        return None

    def reject(self, rule_id: str, reason: str = "") -> Optional[dict[str, Any]]:
        """拒绝规则草稿。"""
        rule = self._find(rule_id)
        if rule and rule["status"] == "draft":
            rule["status"] = "rejected"
            rule["reject_reason"] = reason
            self._save()
            return rule
        return None

    def record_application(self, rule_id: str, success: bool) -> None:
        """记录规则被应用后的结果（用于 effectiveness 追踪）。"""
        rule = self._find(rule_id)
        if rule is None:
            return
        rule["applied_count"] += 1
        if success:
            rule["success_after"] += 1
        # 更新 effectiveness
        if rule["applied_count"] > 0:
            rule["effectiveness"] = rule["success_after"] / rule["applied_count"]
        # 如果连续失败 > 3次，标记为 deprecated
        if rule["applied_count"] >= 3 and rule["effectiveness"] < 0.3:
            rule["status"] = "deprecated"
        self._save()

    def get_approved(self) -> list[dict[str, Any]]:
        """获取所有已审批的规则。"""
        return [r for r in self._data["rules"] if r["status"] == "approved"]

    def get_drafts(self) -> list[dict[str, Any]]:
        """获取所有待审批的草稿。"""
        return [r for r in self._data["rules"] if r["status"] == "draft"]

    def get_by_trigger(self, trigger_pattern: str) -> list[dict[str, Any]]:
        """根据 trigger pattern 查找规则。"""
        return [
            r for r in self.get_approved()
            if trigger_pattern in r.get("trigger_pattern", "")
            or r.get("trigger_pattern", "") in trigger_pattern
        ]

    def get_rules_for_prompt(self, context: str) -> str:
        """生成注入 LLM prompt 的规则文本。"""
        rules = self.get_approved()
        if not rules:
            return ""
        lines = ["[Meta-Rules]"]
        for r in rules:
            lines.append(f"- {r['rule_text']}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        rules = self._data["rules"]
        return {
            "total": len(rules),
            "draft": sum(1 for r in rules if r["status"] == "draft"),
            "approved": sum(1 for r in rules if r["status"] == "approved"),
            "rejected": sum(1 for r in rules if r["status"] == "rejected"),
            "deprecated": sum(1 for r in rules if r["status"] == "deprecated"),
            "avg_effectiveness": (
                sum(r["effectiveness"] for r in rules if r["status"] == "approved")
                / max(1, sum(1 for r in rules if r["status"] == "approved"))
            ),
        }

    def _find(self, rule_id: str) -> Optional[dict[str, Any]]:
        for r in self._data["rules"]:
            if r["id"] == rule_id:
                return r
        return None

    def _next_id(self) -> str:
        existing = [r["id"] for r in self._data["rules"]]
        max_num = 0
        for eid in existing:
            if eid.startswith("rule_"):
                try:
                    num = int(eid[5:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        return f"rule_{max_num + 1:03d}"
