"""M2-4: GUI 模式记忆 (持久化 last_mode 到 config.json)

关闭 GUI 后再打开, 恢复上次选择的 Tab (对话/编程).
"""
import json
from pathlib import Path


CONFIG_PATH = Path.home() / ".TuringClaw" / "config.json"


def _load_config() -> dict:
    """读取 config.json (不存在返回空 dict)"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] 读取 config.json 失败: {e}")
    return {}


def _save_config(config: dict) -> bool:
    """写入 config.json (失败不抛异常)"""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[WARN] 写入 config.json 失败: {e}")
        return False


def get_last_mode() -> str:
    """获取上次模式: 'chat' 或 'codex', 默认 'chat'"""
    config = _load_config()
    return config.get("last_mode", "chat")


def set_last_mode(mode: str) -> None:
    """保存当前模式到 config.json

    Args:
        mode: 'chat' 或 'codex'
    """
    if mode not in ("chat", "codex"):
        return
    config = _load_config()
    config["last_mode"] = mode
    _save_config(config)
