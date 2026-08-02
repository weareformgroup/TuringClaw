# -*- coding: utf-8 -*-
"""
Triple Gate — 三安全维度流水线门控

GSM V10: 三个安全维度流水线过滤，互相影响。
  维度1: 隐私路由 S1/S2/S3 (数据能不能出去)
  维度2: 置信门控 AUTO/AUTO_LOG/CONFIRM/BLOCK (操作能不能自主)
  维度3: 安全策略层 (系统允不允许)

三维度互相影响:
  - S3(强制本地) → 置信门控自动+1级（数据不出本地，风险低）
  - 置信门控CONFIRM → 用户不在线 → 跳过任务
  - 安全策略拦截 → 触发SECURITY_BLOCKED错误
"""
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class GateDecision:
    """门控决策结果。"""
    allowed: bool
    auto_level: str  # AUTO / AUTO_LOG / CONFIRM / BLOCK
    privacy_level: str = "S1"  # S1 / S2 / S3
    security_blocked: bool = False
    reason: str = ""
    gate_hint: str = ""  # 传递给后续处理的提示


# 风险矩阵: 操作类型 × 自主等级
RISK_MATRIX = {
    # 低风险操作 → AUTO
    "read_file": "AUTO",
    "list_dir": "AUTO",
    "web_search": "AUTO",
    "web_fetch": "AUTO",
    "search_brain": "AUTO",

    # 中风险操作 → AUTO_LOG
    "write_file": "AUTO_LOG",
    "exec_command": "AUTO_LOG",
    "put_brain_page": "AUTO_LOG",

    # 高风险操作 → CONFIRM
    "delete_file": "CONFIRM",
    "git_push": "CONFIRM",
    "send_message": "CONFIRM",
    "install_package": "CONFIRM",

    # 极高风险 → BLOCK
    "delete_directory": "BLOCK",
    "format_disk": "BLOCK",
    "modify_system_config": "BLOCK",
}

# 安全策略关键词（模拟 OpenClaw 安全策略层）
SECURITY_BLOCK_PATTERNS = [
    "rm -rf /",
    "format c:",
    "del /f /s /q C:\\",
    "diskpart clean",
]


class TripleGate:
    """三安全维度流水线门控。"""

    def evaluate(
        self,
        operation: str,
        privacy_level: str = "S1",
        user_online: bool = True,
        is_local: bool = False,
    ) -> GateDecision:
        """
        评估操作是否允许执行。

        Args:
            operation: 操作类型 (read_file, write_file, exec_command 等)
            privacy_level: 隐私路由级别 (S1/S2/S3)
            user_online: 用户是否在线（影响CONFIRM的处理）
            is_local: 是否在本地执行（S3路径）
        """
        # 维度1: 隐私路由已经在外部完成，这里接收结果

        # 维度2: 置信门控
        base_level = RISK_MATRIX.get(operation, "CONFIRM")  # 未知操作默认CONFIRM

        # 三维度互相影响: S3(本地) → 自动+1级
        if privacy_level == "S3" or is_local:
            if base_level == "CONFIRM":
                auto_level = "AUTO_LOG"
                gate_hint = "S3 local: risk downgraded CONFIRM→AUTO_LOG"
            elif base_level == "AUTO_LOG":
                auto_level = "AUTO"
                gate_hint = "S3 local: risk downgraded AUTO_LOG→AUTO"
            elif base_level == "BLOCK":
                auto_level = "CONFIRM"  # BLOCK降一级到CONFIRM，但仍需确认
                gate_hint = "S3 local: risk downgraded BLOCK→CONFIRM"
            else:
                auto_level = base_level
                gate_hint = ""
        else:
            auto_level = base_level
            gate_hint = ""

        # 维度3: 安全策略层
        security_blocked = self._check_security_policy(operation)

        if security_blocked:
            return GateDecision(
                allowed=False,
                auto_level="BLOCK",
                privacy_level=privacy_level,
                security_blocked=True,
                reason=f"Security policy blocked: {operation}",
                gate_hint=gate_hint,
            )

        # 处理 CONFIRM 但用户不在线
        if auto_level == "CONFIRM" and not user_online:
            return GateDecision(
                allowed=False,
                auto_level="CONFIRM",
                privacy_level=privacy_level,
                reason="CONFIRM required but user offline",
                gate_hint=gate_hint,
            )

        # 处理 BLOCK
        if auto_level == "BLOCK":
            return GateDecision(
                allowed=False,
                auto_level="BLOCK",
                privacy_level=privacy_level,
                reason="Operation blocked by risk matrix",
                gate_hint=gate_hint,
            )

        return GateDecision(
            allowed=True,
            auto_level=auto_level,
            privacy_level=privacy_level,
            gate_hint=gate_hint,
        )

    def _check_security_policy(self, operation: str) -> bool:
        """检查安全策略层是否拦截。"""
        op_lower = operation.lower()
        for pattern in SECURITY_BLOCK_PATTERNS:
            if pattern.lower() in op_lower:
                return True
        return False


# 全局单例
_gate: Optional[TripleGate] = None


def get_triple_gate() -> TripleGate:
    global _gate
    if _gate is None:
        _gate = TripleGate()
    return _gate
