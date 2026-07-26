# -*- coding: utf-8 -*-
"""
QClaw Bridge — 从 QClaw 的 openclaw.json 自动提取模型配置，桥接给 TuringClaw GUI。

这样 TuringClaw 不需要单独的 API key，直接复用 QClaw 的模型池：
- Ollama 本地模型 (qwen2.5:14b, deepseek-r1:14b, qwq 等)
- MiniMax 云端模型 (MiniMax-M3)

原理：读取 QClaw gateway 配置文件中的 models.providers，
为每个 provider 生成一个预配置好的 ProviderInfo（api_key 直接烘焙）。

安全：只读本地文件，不暴露 key 到日志/外部。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


_OPENCLAW_CONFIG_CANDIDATES = [
    Path.home() / ".qclaw" / "openclaw.json",
    Path.home() / ".openclaw" / "openclaw.json",
]


def _find_config() -> Optional[Path]:
    for p in _OPENCLAW_CONFIG_CANDIDATES:
        if p.exists():
            return p
    return None


def _extract_providers(cfg: dict) -> List[dict]:
    """从 openclaw.json 提取 Ollama + MiniMax 配置。"""
    result = []
    providers = cfg.get("models", {}).get("providers", {})
    if not providers:
        return result

    # LM Studio 本地（GPU 加速，替代 Ollama）
    lmstudio_url = "http://localhost:1234/v1"
    result.append({
        "name": "lmstudio",
        "display_name": "LM Studio (本地 GPU)",
        "api_key_env": "LMSTUDIO_API_KEY",
        "api_key": "lm-studio",
        "api_base_url": lmstudio_url,
        "models": ["qwen2.5-1.5b-instruct"],
        "default_model": "qwen2.5-1.5b-instruct",
        "free_tier": "完全免费，本地 GPU 加速（RTX 3050）",
        "signup_url": "https://lmstudio.ai/",
        "is_local": True,
        "status": "configured",
    })

    # MiniMax 云端
    minimax = providers.get("minimax")
    if minimax:
        models = [m.get("id") for m in minimax.get("models", []) if m.get("id")]
        result.append({
            "name": "qclaw_minimax",
            "display_name": "MiniMax (QClaw 桥接)",
            "api_key_env": "MINIMAX_API_KEY",
            "api_key": minimax.get("apiKey", ""),
            "api_base_url": minimax.get("baseUrl") or "https://api.minimaxi.com/v1",
            "models": models or ["MiniMax-M3"],
            "default_model": models[0] if models else "MiniMax-M3",
            "free_tier": "QClaw 内置额度（经 QClaw 桥接）",
            "signup_url": "https://www.minimaxi.com/",
            "is_local": False,
            "status": "configured" if minimax.get("apiKey") else "not_configured",
        })

    return result


def get_qclaw_providers() -> Dict[str, "ProviderInfo"]:
    try:
        from gui.providers import ProviderInfo
    except ImportError:
        try:
            from providers import ProviderInfo
        except ImportError:
            class ProviderInfo:
                def __init__(self, **kw):
                    for k, v in kw.items():
                        setattr(self, k, v)

    cfg_path = _find_config()
    if not cfg_path:
        return {}
    try:
        cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[QClawBridge] 无法读取配置: {e}")
        return {}

    raw = _extract_providers(cfg)
    providers = {}
    for p in raw:
        providers[p["name"]] = ProviderInfo(**p)
    print(f"[QClawBridge] 已加载 {len(providers)} 个 QClaw provider: {list(providers.keys())}")
    return providers


def resolve_api_key(provider) -> str:
    """优先用 provider.api_key，回退到 env。"""
    if getattr(provider, "api_key", ""):
        return provider.api_key
    env = getattr(provider, "api_key_env", "")
    if env:
        import os
        return os.environ.get(env, "")
    return ""


if __name__ == "__main__":
    ps = get_qclaw_providers()
    for n, p in ps.items():
        mask = (p.api_key[:6] + "..." + p.api_key[-4:]) if p.api_key and len(p.api_key) > 12 else "***"
        print(f"  {n}: base={p.api_base_url} model={p.default_model} key={mask}")
