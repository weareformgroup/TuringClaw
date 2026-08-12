# -*- coding: utf-8 -*-
"""
Four-Layer Crystallization Linkage — 四层联动机制

GSM V10 B2: 四层结晶的自组织联动。

联动逻辑:
  Layer 4 (统计) 发现模式 → Layer 3 (规则) 创建草稿
  Layer 3 规则改变 → Layer 2 (假设) 更新策略
  Layer 2 假设修改 → Layer 1 (Skill) 更新步骤
  Layer 1 新 Skill 被使用 → 结果反馈到 Layer 4 → 循环

这是四层结晶的"自组织"特性——不需要中央控制器，各层通过事件互相触发。
"""
from typing import Any, Optional
import json
from pathlib import Path
from pathlib import Path
from cognitive.layer4_tacit.execution_intuition import ExecutionIntuitionUpdater
from cognitive.layer4_tacit.tool_usage_stats import ToolUsageStatsUpdater
from cognitive.layer2_framework.bayesian_updater import FrameworkUpdater
from cognitive.layer3_metarules.rules_manager import MetaRulesManager


class CrystallizationLinkage:
    """四层结晶联动器。"""

    # 触发规则创建的失败次数阈值
    FAILURE_THRESHOLD = 3
    # 触发假设更新的证据数量阈值
    EVIDENCE_THRESHOLD = 3

    def __init__(
        self,
        intuition: Optional[ExecutionIntuitionUpdater] = None,
        tool_stats: Optional[ToolUsageStatsUpdater] = None,
        framework: Optional[FrameworkUpdater] = None,
        meta_rules: Optional[MetaRulesManager] = None,
        data_dir: str | Path | None = None,
    ):
        if data_dir is not None:
            self.intuition = intuition or ExecutionIntuitionUpdater(cognitive_dir=data_dir)
            self.tool_stats = tool_stats or ToolUsageStatsUpdater(cognitive_dir=data_dir)
            self.framework = framework or FrameworkUpdater(data_dir=data_dir)
            self.meta_rules = meta_rules or MetaRulesManager(data_dir=data_dir)
        else:
            self.intuition = intuition or ExecutionIntuitionUpdater()
            self.tool_stats = tool_stats or ToolUsageStatsUpdater()
            self.framework = framework or FrameworkUpdater()
            self.meta_rules = meta_rules or MetaRulesManager()
        self._linkage_log: list[dict[str, Any]] = []
        self._linkage_file: Path | None = None
        if data_dir is not None:
            self._linkage_file = Path(data_dir) / "linkage_log.json"
        else:
            self._linkage_file = Path.home() / ".TuringClaw" / "cognitive" / "linkage_log.json"
        self._load_linkage_log()

    def _load_linkage_log(self):
        """从文件加载历史 linkage log。"""
        if self._linkage_file and self._linkage_file.exists():
            try:
                data = json.loads(self._linkage_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._linkage_log = data
            except Exception:
                self._linkage_log = []

    def _save_linkage_log(self):
        """持久化 linkage log 到文件。"""
        if self._linkage_file:
            try:
                self._linkage_file.parent.mkdir(parents=True, exist_ok=True)
                self._linkage_file.write_text(
                    json.dumps(self._linkage_log, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def on_failure(self, trigger: str, failure_description: str, learned_action: str = ""):
        """
        Layer 4 失败事件 → 检查是否触发联动。
        """
        # 1. Layer 4 记录失败
        self.intuition.on_failure(trigger, learned_action, failure_description)

        # 2. 检查是否达到触发 Layer 3 规则创建的阈值
        matching = self.intuition.get_by_trigger(trigger)
        # 使用 evidence_count 而非记录数来判断是否达到阈值
        total_evidence = sum(m.get("evidence_count", 1) for m in matching)
        failure_count = total_evidence

        if failure_count >= self.FAILURE_THRESHOLD:
            # 检查是否已有对应规则（草稿或已审批）
            existing_drafts = self.meta_rules.get_drafts()
            existing_approved = self.meta_rules.get_approved()
            existing = [r for r in existing_drafts + existing_approved if trigger in r.get("trigger_pattern", "")]
            if not existing:
                # 创建规则草稿
                rule_text = self._infer_rule_text(trigger, failure_description, learned_action)
                draft = self.meta_rules.create_draft(
                    trigger_pattern=trigger,
                    rule_text=rule_text,
                    source="tacit",
                    evidence_trigger=trigger,
                    confidence=min(0.8, 0.3 + 0.1 * failure_count),
                )
                self._log_linkage("L4→L3", f"Failure threshold reached for '{trigger}', created rule draft: {rule_text}")

                # 3. 联动到 Layer 2：创建或更新假设
                self._link_to_framework(trigger, failure_description, learned_action)

        return failure_count

    def on_tool_call(self, tool_name: str, context: str, success: bool, latency_ms: float):
        """
        Layer 4 工具调用 → 更新统计 + 可能触发假设更新。
        """
        self.tool_stats.on_tool_call(tool_name, context, success, latency_ms)

        # 检查工具成功率是否异常低
        stats = self.tool_stats.get_tool_stats(tool_name)
        if stats and stats.get("total_calls", 0) >= 5:
            success_rate = stats.get("success_rate", 1.0)
            if success_rate < 0.5:
                # 工具成功率低于50% → 可能需要创建假设
                active_hyps = self.framework.get_by_tag(tool_name)
                if not active_hyps:
                    self.framework.add_hypothesis(
                        statement=f"{tool_name} 工具可靠性低 (success_rate={success_rate:.2f})",
                        prior=0.3,
                        tags=[tool_name, "reliability"],
                    )
                    self._log_linkage("L4→L2", f"Low success rate for {tool_name}, created hypothesis")

    def on_rule_approved(self, rule_id: str):
        """
        Layer 3 规则被审批 → 联动到 Layer 2 假设更新。
        """
        rule = self.meta_rules.get_approved()
        matching = [r for r in rule if r["id"] == rule_id]
        if not matching:
            return

        r = matching[0]
        trigger = r.get("trigger_pattern", "")

        # 查找相关假设并更新
        hyps = self.framework.get_active()
        for hyp in hyps:
            if trigger in hyp.get("statement", "").lower() or trigger in str(hyp.get("tags", [])):
                # 规则审批通过 → 假设置信度降低（说明之前的假设可能不对）
                self.framework.update_belief(
                    hyp["id"],
                    evidence_description=f"Rule approved: {r['rule_text']}",
                    evidence_supports=False,
                    likelihood=0.6,
                )
                self._log_linkage("L3→L2", f"Rule {rule_id} approved, updated hypothesis {hyp['id']}")

    def on_hypothesis_confirmed(self, hypothesis_id: str):
        """
        Layer 2 假设被确认 → 联动到 Layer 1 Skill 更新。
        """
        hyp = self.framework.get_hypothesis(hypothesis_id)
        if hyp and hyp["status"] == "confirmed":
            # 假设被确认 → 应该写入 Skill（Layer 1）
            # 这里只记录日志，实际 Skill 生成需要 LLM 参与
            self._log_linkage(
                "L2→L1",
                f"Hypothesis confirmed: {hyp['statement']}, should update SKILL.md"
            )

    def on_skill_used(self, skill_name: str, success: bool):
        """
        Layer 1 Skill 被使用 → 结果反馈到 Layer 4。
        """
        # Skill 使用结果反馈到工具统计
        self.tool_stats.on_tool_call(skill_name, "skill_usage", success, 0)
        self._log_linkage("L1→L4", f"Skill {skill_name} used, success={success}")

    def get_linkage_log(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._linkage_log[-limit:]


    def auto_approve_check(self) -> list[dict[str, Any]]:
        """Phase 7: Auto-approve rules when evidence >= 5 and tool success rate improved."""
        approved = []
        drafts = self.meta_rules.get_drafts()
        for rule in drafts:
            trigger = rule.get("trigger_pattern", "")
            if not trigger:
                continue
            matching = self.intuition.get_by_trigger(trigger)
            total_evidence = sum(m.get("evidence_count", 1) for m in matching)
            tool_name = trigger.split("_")[0] if "_" in trigger else trigger
            stats = self.tool_stats.load() if hasattr(self.tool_stats, "load") else {}
            tool_data = stats.get("tools", {}).get(tool_name, {})
            success_rate = tool_data.get("success_rate", 0)
            total_calls = tool_data.get("total_calls", 0)
            should_approve = (total_evidence >= 5 and (success_rate > 0.7 or total_calls >= 10))
            if should_approve:
                rule_id = rule.get("id", "")
                result = self.meta_rules.approve(rule_id)
                if result:
                    approved.append(result)
                    self._linkage_log.append({"type": "l3_auto_approved", "rule_id": rule_id, "trigger": trigger, "evidence": total_evidence})
        return approved

    def try_generate_skill(self) -> list[dict[str, Any]]:
        """Phase 7: Generate Layer 1 Skills from confirmed Layer 2 hypotheses."""
        try:
            from cognitive.layer1_skill.skill_generator import SkillGenerator
        except ImportError:
            return []
        gen = SkillGenerator()
        generated = []
        hypotheses = self.framework._load().get("hypotheses", [])
        for hyp in hypotheses:
            if hyp.get("posterior", 0) >= 0.8 and hyp.get("evidence_count", 0) >= 3:
                trigger = hyp.get("trigger_pattern", "")
                related = self.intuition.get_by_trigger(trigger) if trigger else []
                skill = gen.try_generate(hyp, related)
                if skill:
                    generated.append(skill)
                    self._linkage_log.append({"type": "l2_to_l1", "skill_id": skill["id"], "source_hypothesis": hyp.get("id", "")})
        return generated

    def get_stats(self) -> dict[str, Any]:
        stats = {
            "linkage_events": len(self._linkage_log),
            "l4_to_l3": 0,
            "l4_to_l2": 0,
            "l3_to_l2": 0,
            "l2_to_l1": 0,
            "l1_to_l4": 0,
        }
        for l in self._linkage_log:
            d = l.get("direction", l.get("type", ""))
            if d in ("L4→L3", "l4_to_l3"):
                stats["l4_to_l3"] += 1
            elif d in ("L4→L2", "l4_to_l2"):
                stats["l4_to_l2"] += 1
            elif d in ("L3→L2", "l3_to_l2"):
                stats["l3_to_l2"] += 1
            elif d in ("L2→L1", "l2_to_l1"):
                stats["l2_to_l1"] += 1
            elif d in ("L1→L4", "l1_to_l4"):
                stats["l1_to_l4"] += 1
        return stats

    def _link_to_framework(self, trigger: str, failure_desc: str, learned_action: str):
        """Layer 4 联动到 Layer 2：创建或更新假设。"""
        statement = f"针对 '{trigger}' 的当前处理方式是有效的"
        existing = [h for h in self.framework.get_active() if trigger in h.get("statement", "")]

        if existing:
            # 更新已有假设
            hyp = existing[0]
            self.framework.update_belief(
                hyp["id"],
                evidence_description=failure_desc,
                evidence_supports=False,
                likelihood=0.6,
            )
        else:
            # 创建新假设
            self.framework.add_hypothesis(
                statement=statement,
                prior=0.5,
                tags=[trigger, "failure_pattern"],
            )

        self._log_linkage("L4→L2", f"Updated framework for trigger '{trigger}'")

    def _infer_rule_text(self, trigger: str, failure_desc: str, learned_action: str) -> str:
        """从失败模式推断规则文本（简化版，未来可用 LLM）。"""
        if learned_action:
            return f"当遇到 '{trigger}' 时，{learned_action}"
        return f"当遇到 '{trigger}' 时，注意：{failure_desc}"

    def _log_linkage(self, direction: str, description: str):
        entry = {
            "direction": direction,
            "description": description,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        self._linkage_log.append(entry)
        self._save_linkage_log()
