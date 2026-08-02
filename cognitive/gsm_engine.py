# -*- coding: utf-8 -*-
"""
GSM Engine — 完整目标执行引擎 (Level 4)

GSM V10: 目标分解 → 置信门控 → 执行 → 评估 → 完成/错误恢复

这是 GSM 的主入口，编排 AgentLoop 的执行。
不替代 AgentLoop，而是在上面加一层调度。
"""
from typing import Callable, Any, Optional
from datetime import datetime, timezone

from cognitive.goal_detector import GoalDetector, GoalDetection
from cognitive.mini_goal import MiniGoal, MiniGoalExecutor, TaskResult
from cognitive.triple_gate import TripleGate, get_triple_gate
from cognitive.dual_spiral_engine import DualSpiralEngine


class GSMEngine:
    """GSM 主引擎：双模式执行的调度器。"""

    def __init__(self, cognitive_engine: Optional[DualSpiralEngine] = None):
        self.detector = GoalDetector()
        self.gate = get_triple_gate()
        self.executor = MiniGoalExecutor()
        self.cognitive = cognitive_engine  # 可选，用于记录执行经验

    def process_message(
        self,
        message: str,
        task_executor: Callable[[str, str], tuple[bool, str, str]],
        privacy_level: str = "S1",
        user_online: bool = True,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> dict[str, Any]:
        """
        处理用户消息 — 自动判断 Level 并执行。

        Args:
            message: 用户消息
            task_executor: 原子任务执行回调 (task_id, description) → (success, output, error)
            privacy_level: 当前隐私路由级别
            user_online: 用户是否在线
            on_progress: 进度回调

        Returns:
            执行结果字典
        """
        # Step 1: 检测目标等级
        detection = self.detector.detect(message)

        # Level 0-2: 不需要 GSM，交给 AgentLoop
        if detection.level <= 2:
            return {
                "mode": "conversation",
                "level": detection.level,
                "message": message,
            }

        # Level 3-4: 目标模式
        if on_progress:
            on_progress(f"检测到目标 (Level {detection.level}): {detection.title}")

        # Step 2: 三安全维度门控 — 评估整体目标
        gate_decision = self.gate.evaluate(
            operation="exec_command",  # 目标执行涉及命令执行
            privacy_level=privacy_level,
            user_online=user_online,
        )

        if not gate_decision.allowed and gate_decision.auto_level == "BLOCK":
            return {
                "mode": "blocked",
                "level": detection.level,
                "reason": gate_decision.reason,
                "message": f"操作被安全策略阻止: {gate_decision.reason}",
            }

        if not gate_decision.allowed and gate_decision.auto_level == "CONFIRM":
            return {
                "mode": "needs_confirm",
                "level": detection.level,
                "reason": gate_decision.reason,
                "message": "需要用户确认才能执行此目标",
            }

        # Step 3: 创建并执行目标
        goal = MiniGoal(
            title=detection.title,
            tasks=detection.suggested_tasks if detection.suggested_tasks else [message[:50]],
        )

        if on_progress:
            on_progress(f"开始执行，共 {len(goal.tasks)} 个任务")

        # Step 4: 执行（每个任务通过门控后再执行）
        def gated_executor(task_id: str, description: str) -> tuple[bool, str, str]:
            """带门控的任务执行器。"""
            # 简化：根据任务描述推断操作类型
            op_type = self._infer_operation(description)
            task_gate = self.gate.evaluate(
                operation=op_type,
                privacy_level=privacy_level,
                user_online=user_online,
            )

            if not task_gate.allowed:
                return False, "", f"Gate blocked: {task_gate.reason}"

            # 执行任务
            success, output, error = task_executor(task_id, description)

            # Step 5: 记录到认知引擎（如果可用）
            if self.cognitive:
                try:
                    self.cognitive.on_tool_call(op_type, description, success, 0)
                    if not success:
                        self.cognitive.on_failure(
                            trigger=description[:50],
                            failure_description=error[:200],
                            learned_action="",
                        )
                except Exception:
                    pass

            return success, output, error

        def progress_callback(task: TaskResult):
            if on_progress:
                icon = {"done": "[OK]", "failed": "[FAIL]", "running": "[...]", "skipped": "[SKIP]"}.get(task.status, "?")
                on_progress(f"{icon} {task.description}")
                if task.output and task.status == "done":
                    on_progress(f"    → {task.output[:80]}")

        executed_goal = self.executor.execute(goal, gated_executor, progress_callback)

        # Step 6: 返回结果
        return {
            "mode": "goal",
            "level": detection.level,
            "goal": executed_goal,
            "summary": executed_goal.summary(),
            "gate_hint": gate_decision.gate_hint,
            "complexity_factors": detection.complexity_factors,
        }

    def _infer_operation(self, description: str) -> str:
        """从任务描述推断操作类型（简化版）。"""
        desc = description.lower()
        if "删除" in desc or "delete" in desc or "remove" in desc:
            if "目录" in desc or "directory" in desc:
                return "delete_directory"
            return "delete_file"
        if "写入" in desc or "write" in desc or "创建" in desc and "文件" in desc:
            return "write_file"
        if "读取" in desc or "read" in desc or "查看" in desc:
            return "read_file"
        if "运行" in desc or "执行" in desc or "exec" in desc or "run" in desc:
            return "exec_command"
        if "推送" in desc or "push" in desc:
            return "git_push"
        if "安装" in desc or "install" in desc:
            return "install_package"
        if "发送" in desc or "send" in desc:
            return "send_message"
        return "exec_command"  # 默认


# 全局单例
_engine: Optional[GSMEngine] = None


def get_gsm_engine() -> GSMEngine:
    global _engine
    if _engine is None:
        _engine = GSMEngine()
    return _engine
