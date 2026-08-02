# -*- coding: utf-8 -*-
"""
MiniGoal — 轻量目标执行器 (Level 3)

GSM V10: 1-3个任务的简单列表执行，不需要完整DAG。
每个原子任务通过回调函数执行（由 AgentLoop 提供）。
"""
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass
class TaskResult:
    """单个任务执行结果。"""
    task_id: str
    description: str
    status: str = "pending"  # pending / running / done / failed / skipped
    output: str = ""
    error: str = ""
    started_at: str = ""
    completed_at: str = ""


@dataclass
class MiniGoal:
    """轻量目标：1-3个任务的简单列表。"""
    title: str
    tasks: list[str]  # 任务描述列表
    status: str = "active"  # active / completed / failed / cancelled
    results: list[TaskResult] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.results:
            self.results = [
                TaskResult(task_id=f"task_{i+1}", description=desc)
                for i, desc in enumerate(self.tasks)
            ]

    def next_task(self) -> Optional[TaskResult]:
        """获取下一个待执行的任务。"""
        for r in self.results:
            if r.status == "pending":
                return r
        return None

    def is_complete(self) -> bool:
        """检查是否所有任务都完成了。"""
        return all(r.status in ("done", "failed", "skipped") for r in self.results)

    def summary(self) -> str:
        """生成完成摘要。"""
        done = sum(1 for r in self.results if r.status == "done")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        total = len(self.results)

        lines = [f"目标完成: {self.title}"]
        lines.append(f"任务: {done}/{total} 完成, {failed} 失败, {skipped} 跳过")
        for r in self.results:
            icon = {"done": "[OK]", "failed": "[FAIL]", "skipped": "[SKIP]", "pending": "[...]", "running": "[...]"} .get(r.status, "?")
            lines.append(f"  {icon} {r.description}")
            if r.output:
                lines.append(f"      → {r.output[:100]}")
            if r.error:
                lines.append(f"      ✗ {r.error[:100]}")
        return "\n".join(lines)


class MiniGoalExecutor:
    """轻量目标执行器。"""

    def __init__(self, cognitive_dir: str | Path | None = None):
        if cognitive_dir is None:
            cognitive_dir = Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir = Path(cognitive_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "goal_history.json"

    def execute(
        self,
        goal: MiniGoal,
        task_executor: Callable[[str, str], tuple[bool, str, str]],
        on_progress: Optional[Callable[[TaskResult], None]] = None,
    ) -> MiniGoal:
        """
        执行 MiniGoal。

        Args:
            goal: 要执行的目标
            task_executor: 回调函数 (task_id, description) → (success, output, error)
            on_progress: 每个任务完成后回调

        Returns:
            完成后的 goal（含结果）
        """
        while not goal.is_complete():
            task = goal.next_task()
            if task is None:
                break

            task.status = "running"
            task.started_at = datetime.now(timezone.utc).isoformat()

            if on_progress:
                on_progress(task)

            try:
                success, output, error = task_executor(task.task_id, task.description)
                task.status = "done" if success else "failed"
                task.output = output or ""
                task.error = error or ""
            except Exception as e:
                task.status = "failed"
                task.error = str(e)

            task.completed_at = datetime.now(timezone.utc).isoformat()

            if on_progress:
                on_progress(task)

            # 如果任务失败，可以选择跳过后续任务（简化策略）
            if task.status == "failed":
                # 跳过剩余任务
                for r in goal.results:
                    if r.status == "pending":
                        r.status = "skipped"
                        r.error = "Skipped due to previous failure"
                break

        goal.status = "completed" if goal.is_complete() else "failed"
        goal.completed_at = datetime.now(timezone.utc).isoformat()

        # 保存历史
        self._save_history(goal)

        return goal

    def _save_history(self, goal: MiniGoal) -> None:
        """保存目标执行历史。"""
        history = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass

        entry = {
            "title": goal.title,
            "status": goal.status,
            "tasks": [
                {
                    "id": r.task_id,
                    "description": r.description,
                    "status": r.status,
                    "output": r.output[:200],
                    "error": r.error[:200],
                }
                for r in goal.results
            ],
            "created_at": goal.created_at,
            "completed_at": goal.completed_at,
        }
        history.append(entry)

        # 只保留最近100条
        history = history[-100:]
        self.history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
