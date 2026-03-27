# -*- coding: utf-8 -*-
"""
TuringClaw Privacy Router - 三级隐私路由机制
基于 EdgeClaw GuardAgent 协议实现

级别说明：
  S1 - 默认模式：数据直通，发送到云端或本地模型
  S2 - 脱敏模式：敏感数据脱敏后发送，响应后还原
  S3 - 安全模式：强制使用本地 Ollama 模型，数据不出本地
"""

import re
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


# ─────────────────────────────────────────────
# 1. 数据结构定义
# ─────────────────────────────────────────────

@dataclass
class DetectionResult:
    """检测结果"""
    level: str          # "S1" / "S2" / "S3"
    hits: List[str]     # 命中的规则名称列表
    reason: str         # 人类可读的原因说明


@dataclass
class DesensitizeResult:
    """脱敏结果"""
    original: str               # 原始文本
    sanitized: str              # 脱敏后文本
    mapping: Dict[str, str]     # 脱敏映射表 {占位符: 原始值}
    hit_types: List[str]        # 命中的脱敏类型


@dataclass
class RouteDecision:
    """路由决策"""
    level: str              # "S1" / "S2" / "S3"
    use_local: bool         # 是否强制使用本地模型
    sanitized_text: str     # 发送给模型的文本（可能已脱敏）
    mapping: Dict[str, str] # 脱敏映射表（S2 时用于还原）
    hits: List[str]         # 命中的规则
    reason: str             # 路由原因说明


# ─────────────────────────────────────────────
# 2. 敏感度检测器
# ─────────────────────────────────────────────

# S3 级别：高度敏感，强制本地处理
S3_PATTERNS = {
    "password_kv":    (r'(?i)(?:password|passwd|pwd|密码(?:是)?|口令)\s*[:=：]?\s*\S+',
                       "密码"),
    "api_key_kv":     (r'(?i)(api[_\-]?key|apikey|secret[_\-]?key|access[_\-]?token)\s*[:=]\s*\S+',
                       "API Key 键值对"),
    "private_key":    (r'-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----',
                       "私钥"),
    "credit_card":    (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9]{2})[0-9]{12}|3[47][0-9]{13})\b',
                       "信用卡号"),
    "medical_kw":     (r'(?i)(病历|诊断|处方|医嘱|血型|HIV|癌症|肿瘤)',
                       "医疗敏感词"),
}

# S2 级别：中等敏感，脱敏后发送
S2_PATTERNS = {
    "cn_phone":       (r'(?<!\d)1[3-9]\d{9}(?!\d)',
                       "中国手机号"),
    "cn_idcard":      (r'\b\d{17}[\dXx]\b',
                       "身份证号"),
    "bank_card":      (r'\b(?:62|60|64)\d{14,17}\b',
                       "银行卡号"),
    "email":          (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
                       "电子邮箱"),
    "ipv4_private":   (r'\b(?:192\.168|10\.\d+|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b',
                       "内网 IP 地址"),
    "cn_name_kv":     (r'(?i)(姓名|name|用户名)\s*[:：]\s*[\u4e00-\u9fa5A-Za-z]{2,10}',
                       "姓名键值对"),
}

# S1 级别关键词（仅记录，不脱敏）
S1_KEYWORDS = [
    "token", "key", "secret", "auth", "credential",
    "密钥", "凭证", "授权"
]


class PrivacyDetector:
    """
    敏感度检测器
    使用规则引擎（正则 + 关键词）检测文本敏感度
    """

    def detect(self, text: str) -> DetectionResult:
        """
        检测文本敏感度，返回 DetectionResult
        优先级：S3 > S2 > S1
        """
        hits = []

        # 检测 S3 级别
        for rule_name, (pattern, desc) in S3_PATTERNS.items():
            if re.search(pattern, text):
                hits.append(f"S3:{rule_name}({desc})")

        if hits:
            return DetectionResult(
                level="S3",
                hits=hits,
                reason="检测到高度敏感数据（" + "、".join(h.split("(")[1].rstrip(")") for h in hits) + "），强制本地处理"
            )

        # 检测 S2 级别
        for rule_name, (pattern, desc) in S2_PATTERNS.items():
            if re.search(pattern, text):
                hits.append(f"S2:{rule_name}({desc})")

        if hits:
            return DetectionResult(
                level="S2",
                hits=hits,
                reason="检测到敏感数据（" + "、".join(h.split("(")[1].rstrip(")") for h in hits) + "），将脱敏后处理"
            )

        # 检测 S1 级别（仅记录）
        s1_hits = [kw for kw in S1_KEYWORDS if kw.lower() in text.lower()]
        if s1_hits:
            return DetectionResult(
                level="S1",
                hits=[f"S1:keyword({kw})" for kw in s1_hits],
                reason="检测到潜在敏感关键词（" + "、".join(s1_hits) + "），正常处理"
            )

        return DetectionResult(level="S1", hits=[], reason="未检测到敏感数据")


# ─────────────────────────────────────────────
# 3. 脱敏处理器
# ─────────────────────────────────────────────

class Desensitizer:
    """
    脱敏处理器
    对 S2 级别数据进行脱敏，保留占位符用于还原
    """

    def desensitize(self, text: str) -> DesensitizeResult:
        """对文本进行脱敏处理"""
        result = text
        mapping = {}
        hit_types = []
        counter = [0]

        def replace(pattern, fmt_fn, type_name):
            nonlocal result
            def _replace(m):
                original = m.group(0)
                placeholder = f"[REDACTED_{type_name}_{counter[0]}]"
                counter[0] += 1
                mapping[placeholder] = original
                return fmt_fn(original)
            new_result = re.sub(pattern, _replace, result)
            if new_result != result:
                hit_types.append(type_name)
                result = new_result

        # 手机号：138****1234
        replace(
            r'(?<!\d)1[3-9]\d{9}(?!\d)',
            lambda s: s[:3] + "****" + s[7:],
            "PHONE"
        )

        # 身份证：110101****1234
        replace(
            r'\b\d{17}[\dXx]\b',
            lambda s: s[:6] + "****" + s[14:],
            "IDCARD"
        )

        # 银行卡：6222****1234
        replace(
            r'\b(?:62|60|64)\d{14,17}\b',
            lambda s: s[:4] + "****" + s[-4:],
            "BANKCARD"
        )

        # 邮箱：u***@example.com
        replace(
            r'\b([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b',
            lambda s: s[0] + "***@" + s.split("@")[1],
            "EMAIL"
        )

        # 内网 IP：192.168.*.*
        replace(
            r'\b((?:192\.168|10\.\d+|172\.(?:1[6-9]|2\d|3[01]))\.\d+)\.\d+\b',
            lambda s: ".".join(s.split(".")[:2]) + ".*.*",
            "PRIVATE_IP"
        )

        # 姓名键值对：姓名: ***
        replace(
            r'(?:姓名|name|用户名)\s*[:：]\s*[\u4e00-\u9fa5A-Za-z]{2,10}',
            lambda s: re.sub(r'([:：]\s*)[\u4e00-\u9fa5A-Za-z]{2,10}', r'\1***', s, flags=re.IGNORECASE),
            "NAME"
        )

        return DesensitizeResult(
            original=text,
            sanitized=result,
            mapping=mapping,
            hit_types=hit_types
        )

    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        """将脱敏占位符还原为原始值（用于响应后处理）"""
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result


# ─────────────────────────────────────────────
# 4. 路由决策器
# ─────────────────────────────────────────────

class PrivacyRouter:
    """
    路由决策器
    根据检测结果决定数据路由方式
    """

    def __init__(self):
        self.detector = PrivacyDetector()
        self.desensitizer = Desensitizer()
        self._manual_level: Optional[str] = None  # 用户手动覆盖级别

    def set_manual_level(self, level: Optional[str]):
        """手动设置安全级别（None 表示自动检测）"""
        assert level in (None, "S1", "S2", "S3"), f"Invalid level: {level}"
        self._manual_level = level

    def route(self, text: str) -> RouteDecision:
        """
        对输入文本进行路由决策
        返回 RouteDecision，包含路由级别、处理后文本、脱敏映射
        """
        # 自动检测
        detection = self.detector.detect(text)

        # 用户手动覆盖（只能提升安全级别，不能降低）
        level = detection.level
        if self._manual_level:
            level_order = {"S1": 1, "S2": 2, "S3": 3}
            if level_order.get(self._manual_level, 0) > level_order.get(level, 0):
                level = self._manual_level

        if level == "S3":
            return RouteDecision(
                level="S3",
                use_local=True,
                sanitized_text=text,   # S3 不脱敏，直接本地处理
                mapping={},
                hits=detection.hits,
                reason=detection.reason
            )

        elif level == "S2":
            desen = self.desensitizer.desensitize(text)
            return RouteDecision(
                level="S2",
                use_local=False,
                sanitized_text=desen.sanitized,
                mapping=desen.mapping,
                hits=detection.hits,
                reason=detection.reason
            )

        else:  # S1
            return RouteDecision(
                level="S1",
                use_local=False,
                sanitized_text=text,
                mapping={},
                hits=detection.hits,
                reason=detection.reason
            )


# ─────────────────────────────────────────────
# 5. 审计日志
# ─────────────────────────────────────────────

class PrivacyAuditLogger:
    """
    隐私路由审计日志
    记录每条消息的路由决策
    """

    def __init__(self, log_path: str = None):
        if log_path is None:
            log_path = str(Path.home() / ".TuringClaw" / "privacy_audit.log")
        self.log_path = log_path
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    def log(self, decision: RouteDecision, msg_preview: str = ""):
        """记录路由决策"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": decision.level,
            "use_local": decision.use_local,
            "hits": decision.hits,
            "reason": decision.reason,
            "msg_preview": msg_preview[:30] + "..." if len(msg_preview) > 30 else msg_preview
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] PrivacyAuditLogger: {e}")

    def get_recent(self, n: int = 20) -> List[dict]:
        """获取最近 n 条审计记录"""
        try:
            if not Path(self.log_path).exists():
                return []
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(l) for l in lines[-n:] if l.strip()]
        except Exception:
            return []


# ─────────────────────────────────────────────
# 6. 全局单例
# ─────────────────────────────────────────────

privacy_router = PrivacyRouter()
privacy_audit_logger = PrivacyAuditLogger()
