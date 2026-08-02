# -*- coding: utf-8 -*-
"""
GSM Goal Mode — 双模式执行的判断和调度

GSM V10: 渐进式自主等级 (5个Level)
  Level 0: 纯对话 (AgentLoop直接回复)
  Level 1: 单步工具调用 (AgentLoop直接处理)
  Level 2: 多步工具链 (AgentLoop max_iterations)
  Level 3: 轻量目标 (MiniGoal, 1-3任务, 简单列表)
  Level 4: 完整目标 (GSMEngine, DAG + 门控 + 错误恢复)

这是确定性代码（不调LLM），根据消息特征判断用哪个Level。
"""
import re
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GoalDetection:
    """目标检测结果。"""
    level: int  # 0-4
    is_goal: bool = False
    title: str = ""
    estimated_steps: int = 1
    complexity_factors: list[str] = field(default_factory=list)
    suggested_tasks: list[str] = field(default_factory=list)


class GoalDetector:
    """检测用户消息是否需要升级到目标模式。确定性代码，不调LLM。"""

    # Level 3/4 触发关键词
    GOAL_KEYWORDS = [
        "帮我做", "帮我实现", "帮我完成", "帮我修复", "帮我检查",
        "帮我创建", "帮我搭建", "帮我部署", "帮我分析", "帮我优化",
        "帮我重构", "帮我迁移", "帮我测试", "帮我编写", "帮我设计",
    ]

    # Level 4 特征：涉及多步骤/多文件
    COMPLEX_INDICATORS = [
        "完整的", "整个", "所有", "全部", "从零", "从头",
        "端到端", "一步到位", "一条龙",
    ]

    # Level 4 特征：涉及多个技术栈
    MULTI_STACK = [
        "前端", "后端", "数据库", "部署", "CI/CD", "测试",
        "文档", "API", "UI", "架构",
    ]

    def detect(self, message: str) -> GoalDetection:
        """分析消息，返回目标检测结果。"""
        msg_lower = message.lower()

        # 检查是否有目标关键词
        has_goal_keyword = any(kw in message for kw in self.GOAL_KEYWORDS)

        if not has_goal_keyword:
            # 检查是否是工具调用模式（Level 1-2）
            tool_indicators = ["读取", "查看", "列出", "搜索", "运行", "执行", "安装"]
            if any(kw in message for kw in tool_indicators):
                return GoalDetection(level=1, title=message[:50])
            return GoalDetection(level=0, title=message[:50])

        # 有目标关键词 → Level 3 或 4
        complexity_factors = []
        suggested_tasks = self._extract_tasks(message)

        # 检查复杂度指标
        for indicator in self.COMPLEX_INDICATORS:
            if indicator in message:
                complexity_factors.append(f"complex_indicator: {indicator}")

        # 检查多技术栈
        stack_count = sum(1 for s in self.MULTI_STACK if s in message)
        if stack_count >= 2:
            complexity_factors.append(f"multi_stack: {stack_count} stacks")

        # 检查任务数量
        if len(suggested_tasks) > 3:
            complexity_factors.append(f"many_tasks: {len(suggested_tasks)}")

        # 判断 Level
        if len(complexity_factors) >= 2 or len(suggested_tasks) > 5:
            level = 4  # 完整目标
        else:
            level = 3  # 轻量目标

        return GoalDetection(
            level=level,
            is_goal=True,
            title=self._extract_title(message),
            estimated_steps=max(1, len(suggested_tasks)),
            complexity_factors=complexity_factors,
            suggested_tasks=suggested_tasks,
        )

    def _extract_tasks(self, message: str) -> list[str]:
        """从消息中提取任务（简化版，不调LLM）。"""
        tasks = []

        # 按分号、逗号、"然后"、"接着"分割
        parts = re.split(r'[；;，,]|然后|接着|之后|再', message)

        for part in parts:
            part = part.strip()
            if len(part) > 5 and any(kw in part for kw in self.GOAL_KEYWORDS + ["读取", "查看", "运行", "测试", "修复", "创建", "安装"]):
                tasks.append(part)

        return tasks if tasks else [message[:50]]

    def _extract_title(self, message: str) -> str:
        """提取目标标题。"""
        # 去掉"帮我"等前缀
        for kw in self.GOAL_KEYWORDS:
            if message.startswith(kw):
                rest = message[len(kw):].strip()
                return rest[:50] if rest else message[:50]
        return message[:50]


# 全局单例
_detector: Optional[GoalDetector] = None


def get_goal_detector() -> GoalDetector:
    global _detector
    if _detector is None:
        _detector = GoalDetector()
    return _detector
