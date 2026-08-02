# -*- coding: utf-8 -*-
"""
Layer 2: Framework — Bayesian Belief Updater

GSM V10 B2: 四层结晶机制中的认知层。
存储假设库，用贝叶斯后验更新置信度。

核心公式: P(H|E) = P(E|H) * P(H) / P(E)

数据结构 (framework.json):
{
  "hypotheses": [
    {
      "id": "hyp_001",
      "statement": "Ollama 连接是可靠的",
      "prior": 0.8,           // 先验概率
      "posterior": 0.8,       // 后验概率（更新后的置信度）
      "evidence_count": 0,    // 证据数量
      "evidence_for": 0,      // 支持证据数
      "evidence_against": 0,  // 反对证据数
      "status": "active",     // active / deprecated / confirmed
      "created_at": "2026-07-24T...",
      "updated_at": "2026-07-24T...",
      "tags": ["infrastructure", "ollama"]
    }
  ],
  "version": 1
}
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class FrameworkUpdater:
    """贝叶斯假设库更新器。"""

    def __init__(self, data_dir: str | Path | None = None):
        if data_dir is None:
            data_dir = Path.home() / ".TuringClaw" / "cognitive"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "framework.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"hypotheses": [], "version": 1}

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def add_hypothesis(
        self,
        statement: str,
        prior: float = 0.5,
        tags: list[str] = None,
    ) -> dict[str, Any]:
        """添加新假设。"""
        hyp_id = self._next_id()
        now = datetime.now(timezone.utc).isoformat()
        hyp = {
            "id": hyp_id,
            "statement": statement,
            "prior": prior,
            "posterior": prior,
            "evidence_count": 0,
            "evidence_for": 0,
            "evidence_against": 0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "tags": tags or [],
        }
        self._data["hypotheses"].append(hyp)
        self._save()
        return hyp

    def update_belief(
        self,
        hypothesis_id: str,
        evidence_description: str,
        evidence_supports: bool,
        likelihood: float = 0.7,
    ) -> dict[str, Any]:
        """
        贝叶斯更新：根据新证据更新假设的后验概率。

        Args:
            hypothesis_id: 假设ID
            evidence_description: 证据描述
            evidence_supports: True=支持假设, False=反对假设
            likelihood: P(E|H) — 如果假设为真，观察到此证据的概率

        Returns:
            更新后的假设条目
        """
        hyp = self._find(hypothesis_id)
        if hyp is None:
            raise ValueError(f"Hypothesis not found: {hypothesis_id}")

        prior = hyp["posterior"]  # 用当前后验作为新先验

        if evidence_supports:
            # P(H|E) = P(E|H) * P(H) / P(E)
            # P(E) = P(E|H)*P(H) + P(E|¬H)*(1-P(H))
            p_e_given_not_h = 1.0 - likelihood  # 简化：P(E|¬H) = 1 - P(E|H)
            p_e = likelihood * prior + p_e_given_not_h * (1 - prior)
            posterior = (likelihood * prior) / p_e if p_e > 0 else prior

            hyp["evidence_for"] += 1
        else:
            # 反对证据：P(¬E|H) 更高
            p_not_e_given_h = 1.0 - likelihood
            p_not_e_given_not_h = likelihood
            p_not_e = p_not_e_given_h * prior + p_not_e_given_not_h * (1 - prior)
            posterior = (p_not_e_given_h * prior) / p_not_e if p_not_e > 0 else prior

            hyp["evidence_against"] += 1

        # 钳制到 [0.01, 0.99] 避免极端值
        posterior = max(0.01, min(0.99, posterior))

        hyp["posterior"] = posterior
        hyp["evidence_count"] += 1
        hyp["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 状态更新
        if posterior < 0.3:
            hyp["status"] = "deprecated"  # 假设很可能不成立
        elif posterior > 0.8 and hyp["evidence_count"] >= 3:
            hyp["status"] = "confirmed"   # 假设高度可信

        self._save()
        return hyp

    def get_hypothesis(self, hypothesis_id: str) -> Optional[dict[str, Any]]:
        return self._find(hypothesis_id)

    def get_by_tag(self, tag: str) -> list[dict[str, Any]]:
        return [h for h in self._data["hypotheses"] if tag in h.get("tags", [])]

    def get_active(self) -> list[dict[str, Any]]:
        return [h for h in self._data["hypotheses"] if h["status"] == "active"]

    def get_deprecated(self) -> list[dict[str, Any]]:
        return [h for h in self._data["hypotheses"] if h["status"] == "deprecated"]

    def get_confirmed(self) -> list[dict[str, Any]]:
        return [h for h in self._data["hypotheses"] if h["status"] == "confirmed"]

    def get_stats(self) -> dict[str, Any]:
        hyps = self._data["hypotheses"]
        return {
            "total": len(hyps),
            "active": sum(1 for h in hyps if h["status"] == "active"),
            "deprecated": sum(1 for h in hyps if h["status"] == "deprecated"),
            "confirmed": sum(1 for h in hyps if h["status"] == "confirmed"),
            "avg_confidence": (
                sum(h["posterior"] for h in hyps) / len(hyps) if hyps else 0
            ),
        }

    def needs_reflection(self) -> list[dict[str, Any]]:
        """返回需要反思的假设（posterior < 0.3）。"""
        return [h for h in self._data["hypotheses"] if h["posterior"] < 0.3 and h["status"] == "active"]

    def _find(self, hyp_id: str) -> Optional[dict[str, Any]]:
        for h in self._data["hypotheses"]:
            if h["id"] == hyp_id:
                return h
        return None

    def _next_id(self) -> str:
        existing = [h["id"] for h in self._data["hypotheses"]]
        max_num = 0
        for eid in existing:
            if eid.startswith("hyp_"):
                try:
                    num = int(eid[4:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        return f"hyp_{max_num + 1:03d}"
