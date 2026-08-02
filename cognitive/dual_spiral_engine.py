# -*- coding: utf-8 -*-
"""
M6: Dual Spiral Engine — ties together Layer 4 (tacit) + calibration + self-harness.
This is the main entry point for the GSM V10 cognitive system.
"""
import json
from cognitive.layer4_tacit.tool_usage_stats import ToolUsageStatsUpdater
from cognitive.layer4_tacit.execution_intuition import ExecutionIntuitionUpdater
from cognitive.layer4_tacit.prompt_patterns import PromptPatternsRecorder
from cognitive.layer2_framework.bayesian_updater import FrameworkUpdater
from cognitive.layer3_metarules.rules_manager import MetaRulesManager
from cognitive.crystallization_linkage import CrystallizationLinkage
from cognitive.calibration.mentor_feedback import MentorFeedbackCollector
from cognitive.calibration.market_validation import MarketValidationTracker
from cognitive.calibration.tacit_distillation import TacitDistiller
from cognitive.self_harness.writer import SelfHarnessWriter


class DualSpiralEngine:
    """The dual spiral engine: Spiral A (self-evolution) + Spiral B (external calibration).

    Spiral A: Tool usage stats → Intuition → Skill extraction → Framework update
    Spiral B: Mentor feedback → Market validation → Tacit distillation
    Intersection: Self-Harness Writer writes calibrated knowledge into architecture
    """

    def __init__(self):
        # Spiral A components
        self.tool_stats = ToolUsageStatsUpdater()
        self.intuition = ExecutionIntuitionUpdater()
        self.prompt_patterns = PromptPatternsRecorder()

        # Layer 2 & 3 (V10 新增)
        self.framework = FrameworkUpdater()       # Layer 2: 贝叶斯假设库
        self.meta_rules = MetaRulesManager()       # Layer 3: 元认知规则

        # 四层联动器 (V10 新增)
        self.linkage = CrystallizationLinkage(
            intuition=self.intuition,
            tool_stats=self.tool_stats,
            framework=self.framework,
            meta_rules=self.meta_rules,
        )

        # Spiral B components
        self.mentor_feedback = MentorFeedbackCollector()
        self.market_validation = MarketValidationTracker()
        self.tacit_distiller = TacitDistiller()

        # Intersection
        self.writer = SelfHarnessWriter()

    # === Spiral A: Self-evolution ===

    def on_tool_call(self, tool_name: str, context: str, success: bool, latency_ms: float):
        """Record a tool call (Spiral A) — 通过联动器触发四层联动。"""
        self.linkage.on_tool_call(tool_name, context, success, latency_ms)

    def on_task_complete(self, task: str, success: bool, trajectory: dict):
        """Process task completion (Spiral A)."""
        # Generate prediction for market validation
        try:
            pred_id = self.market_validation.record_prediction(
                task=task,
                time_estimate=trajectory.get("estimated_hours", 1),
                risk_level=trajectory.get("risk", "medium"),
                expected_blockers=trajectory.get("expected_blockers", []),
            )
            # Record actual
            self.market_validation.record_actual(
                pred_id,
                time_hours=trajectory.get("actual_hours", 1),
                blockers_encountered=trajectory.get("actual_blockers", []),
                result="success" if success else "failure",
            )
        except TypeError:
            # Fallback: record_prediction may have different signature
            pass

    def auto_approve_rules(self) -> list:
        """Phase 7: Auto-approve Layer 3 rules."""
        return self.linkage.auto_approve_check()

    def auto_generate_skills(self) -> list:
        """Phase 7: Generate Layer 1 Skills."""
        return self.linkage.try_generate_skill()

    def on_failure(self, trigger: str, failure_description: str, learned_action: str = ""):
        """Process a failure event (Spiral A → Layer 4 → 四层联动)。"""
        self.linkage.on_failure(trigger, failure_description, learned_action)

    def on_reflection(self, reflection: str, pattern_detected: str = ""):
        """Process a reflection after task completion (Spiral A)."""
        if pattern_detected:
            self.writer.write(
                title=f"Pattern: {pattern_detected}",
                content=reflection[:500],
                source="spiral_a",
                tags=["reflection", pattern_detected],
            )

    # === Spiral B: External calibration ===

    def on_user_feedback(self, user_message: str, task_context: dict = None) -> dict:
        """Process user feedback (Spiral B)."""
        # Store feedback using MentorFeedbackCollector
        topic = (task_context or {}).get("task", "general")
        entry = self.mentor_feedback.add_feedback(
            topic=topic,
            feedback=user_message,
            rating=3,  # neutral default
            context=json.dumps(task_context or {}, ensure_ascii=False),
        )
        return entry

    def on_user_behavior(self, behavior: str, context: str = "", principle: str = ""):
        """Observe user behavior for tacit distillation (Spiral B)."""
        try:
            self.tacit_distiller.on_user_behavior(behavior, context, principle)
        except Exception:
            pass
        # Write distilled knowledge to architecture via intersection
        self.writer.write(
            title=f"Behavior: {behavior}",
            content=f"Distilled: {principle or behavior}",
            source="spiral_b",
            tags=["behavior", "tacit"],
        )
        return True

    # === Intersection: Self-Harness Writer ===

    def write_knowledge(self, knowledge_type: str, content: str,
                        calibration_data: dict = None) -> dict:
        """Write calibrated knowledge into architecture (intersection point)."""
        return self.writer.write(
            title=knowledge_type,
            content=content,
            source="intersection",
            spiral_b_data=calibration_data,
        )

    # === Status ===

    def status(self) -> dict:
        """Get dual spiral engine status."""
        mentor_stats = self.mentor_feedback.get_stats()
        writer_stats = self.writer.get_stats()
        framework_stats = self.framework.get_stats()
        meta_rules_stats = self.meta_rules.get_stats()
        linkage_stats = self.linkage.get_stats()
        return {
            "spiral_a": {
                "tool_stats_calls": self.tool_stats.total_calls if hasattr(self.tool_stats, 'total_calls') else 0,
                "intuitions": len(self.intuition.load().get('intuitions', [])) if hasattr(self.intuition, 'load') else 0,
                "prompt_patterns": 0,
            },
            "layer2_framework": {
                "total": framework_stats.get("total", 0),
                "active": framework_stats.get("active", 0),
                "confirmed": framework_stats.get("confirmed", 0),
                "deprecated": framework_stats.get("deprecated", 0),
                "avg_confidence": framework_stats.get("avg_confidence", 0),
            },
            "layer3_metarules": {
                "total": meta_rules_stats.get("total", 0),
                "draft": meta_rules_stats.get("draft", 0),
                "approved": meta_rules_stats.get("approved", 0),
                "avg_effectiveness": meta_rules_stats.get("avg_effectiveness", 0),
            },
            "spiral_b": {
                "total_feedback": mentor_stats.get("total", 0),
                "avg_rating": mentor_stats.get("avg_rating", 0),
                "predictions": 0,
                "prediction_accuracy": 0.0,
                "confirmed_observations": len(self.tacit_distiller.get_internalized()) if hasattr(self.tacit_distiller, 'get_internalized') else 0,
            },
            "intersection": {
                "writes": writer_stats.get("total", 0),
                "avg_confidence": writer_stats.get("avg_confidence", 0),
            },
            "linkage": linkage_stats,
        }


if __name__ == "__main__":
    engine = DualSpiralEngine()

    # Simulate Spiral A
    engine.on_tool_call("web_search", "technical_query", True, 3200)
    engine.on_tool_call("read", "config_check", True, 50)
    engine.on_failure("执行操作后", "未验证实际效果", "读回文件验证")

    # Simulate Spiral B
    engine.on_user_feedback("再检查一下，还是不对", {"had_followup_questions": True})
    engine.on_user_behavior("要求反复推敲", "Agent声称完成但未完成", "验证比执行更重要")

    # Simulate intersection
    result = engine.write_knowledge("intuition", "配置变更后必须验证端到端效果")
    print(f"Write result: {result}")

    # Print status
    import json
    print(json.dumps(engine.status(), indent=2, ensure_ascii=False))