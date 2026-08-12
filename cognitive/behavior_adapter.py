# -*- coding: utf-8 -*-
"""
BehaviorAdapter — 认知规则行为适配器

在工具调用前检查 behavior_rules.json，如果匹配规则则应用。
让认知系统的"想"变成"手"的动作。
"""
import json
import os
from pathlib import Path
from typing import Optional


class BehaviorAdapter:
    """读取 behavior_rules.json，在工具调用前应用规则。"""

    def __init__(self, rules_path: str = None):
        if rules_path is None:
            self.rules_path = Path.home() / ".TuringClaw" / "cognitive" / "behavior_rules.json"
        else:
            self.rules_path = Path(rules_path)
        self._rules: list = []
        self._load()

    def _load(self):
        """加载行为规则。"""
        if self.rules_path.exists():
            try:
                self._rules = json.loads(self.rules_path.read_text(encoding="utf-8"))
            except Exception:
                self._rules = []
        return self._rules

    def reload(self):
        """重新加载规则（配置热重载时用）。"""
        self._load()

    def get_apply_rules(self) -> list:
        """获取 action=apply 的规则（approved 规则）。"""
        return [r for r in self._rules if r.get("action") == "apply"]

    def get_suggest_rules(self) -> list:
        """获取 action=suggest 的规则（高置信度草稿）。"""
        return [r for r in self._rules if r.get("action") == "suggest"]

    def check_write(self, content: str, path: str) -> Optional[dict]:
        """
        检查 write 操作是否触发规则。
        返回修正后的操作建议，或 None（不修改）。
        """
        rules = self.get_apply_rules() + self.get_suggest_rules()
        for rule in rules:
            trigger = rule.get("trigger", "")
            if trigger == "write_tool_chinese_truncation":
                # 检查内容是否包含中文且超过 2000 字符
                has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in content)
                if has_chinese and len(content) > 2000:
                    return {
                        "rule_id": rule["id"],
                        "trigger": trigger,
                        "action": "use_dotnet_writealltext",
                        "reason": rule.get("rule", ""),
                        "confidence": rule.get("confidence", 0),
                        "status": rule.get("status", ""),
                    }
        return None

    def check_exec(self, command: str) -> Optional[dict]:
        """检查 exec 操作是否触发规则。"""
        rules = self.get_apply_rules() + self.get_suggest_rules()
        for rule in rules:
            trigger = rule.get("trigger", "")
            if trigger == "codex_cli_timeout":
                if "codex" in command.lower():
                    return {
                        "rule_id": rule["id"],
                        "trigger": trigger,
                        "action": "increase_timeout",
                        "reason": rule.get("rule", ""),
                        "confidence": rule.get("confidence", 0),
                    }
            if trigger == "embed_dim_mismatch":
                if "gbrain" in command.lower() and "embed" in command.lower():
                    return {
                        "rule_id": rule["id"],
                        "trigger": trigger,
                        "action": "use_llama_server_recipe",
                        "reason": rule.get("rule", ""),
                        "confidence": rule.get("confidence", 0),
                    }
        return None

    def check_gbrain(self, command: str) -> Optional[dict]:
        """检查 GBrain 操作是否触发规则。"""
        rules = self.get_apply_rules() + self.get_suggest_rules()
        for rule in rules:
            trigger = rule.get("trigger", "")
            if trigger == "embed_dim_mismatch":
                if "embed" in command.lower() or "pglite" in command.lower():
                    return {
                        "rule_id": rule["id"],
                        "trigger": trigger,
                        "action": "ensure_llama_server_env",
                        "reason": rule.get("rule", ""),
                        "confidence": rule.get("confidence", 0),
                    }
            if trigger == "pglite_wasm_init":
                if "pglite" in command.lower() or "gbrain init" in command.lower():
                    return {
                        "rule_id": rule["id"],
                        "trigger": trigger,
                        "action": "delete_old_pglite_first",
                        "reason": "PGLite WASM 需要删除旧目录后重建",
                        "confidence": rule.get("confidence", 0),
                    }
        return None

    def get_all_rules(self) -> list:
        """获取所有规则。"""
        return self._rules

    def summary(self) -> str:
        """规则摘要。"""
        apply_count = len(self.get_apply_rules())
        suggest_count = len(self.get_suggest_rules())
        return f"BehaviorAdapter: {apply_count} apply + {suggest_count} suggest = {len(self._rules)} total rules"


# === 自测试 ===
if __name__ == "__main__":
    adapter = BehaviorAdapter()
    print(adapter.summary())
    print()
    for r in adapter.get_all_rules():
        action = r.get("action", "?")
        trigger = r.get("trigger", "?")
        rule = r.get("rule", "")[:60]
        print(f"  [{action}] {trigger}: {rule}")

    # 测试 write 检查
    print()
    print("=== Test: write with Chinese > 2000 chars ===")
    long_chinese = "测试" * 1500  # 3000 chars
    result = adapter.check_write(long_chinese, "test.txt")
    print(f"  Result: {result}")

    # 测试 exec 检查
    print()
    print("=== Test: exec with codex ===")
    result = adapter.check_exec("codex --model gpt-4")
    print(f"  Result: {result}")
