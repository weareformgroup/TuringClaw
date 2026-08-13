# -*- coding: utf-8 -*-
"""
Phase 8: 刻意练习 + 清理测试数据 + 确认假设处理

1. 清理测试规则和假设
2. 处理 confirmed 假设（生成知识条目）
3. 生成刻意练习计划
"""
import sys, json, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, r'C:\Users\Administrator\TuringClaw2.0')
sys.path.insert(0, r'C:\Users\Administrator\TuringClaw')

from cognitive.dual_spiral_engine import DualSpiralEngine
from cognitive.crystallization_linkage import CrystallizationLinkage

engine = DualSpiralEngine()
linkage = engine.linkage

print("=== Phase 8: 刻意练习 + 清理 + 确认处理 ===")
print()

# 1. 清理测试规则
print("[1] 清理测试规则...")
rules = engine.meta_rules._load()
test_triggers = {"test_trigger", "test_failure", "test_status_trigger"}
real_rules = [r for r in rules.get("rules", []) if r.get("trigger_pattern") not in test_triggers]
test_count = len(rules.get("rules", [])) - len(real_rules)
engine.meta_rules._rules = real_rules
engine.meta_rules._save()
print(f"  删除 {test_count} 个测试规则，保留 {len(real_rules)} 个真实规则")
for r in real_rules:
    print(f"    [{r['status']}] {r['trigger_pattern']}")

# 2. 清理测试假设
print()
print("[2] 清理测试假设...")
framework = engine.framework._load()
real_hyps = [h for h in framework.get("hypotheses", []) 
             if "test_failure" not in h.get("statement", "") 
             and "test_status_trigger" not in h.get("statement", "")
             and "test_trigger" not in h.get("statement", "")]
test_hyp_count = len(framework.get("hypotheses", [])) - len(real_hyps)
engine.framework._hypotheses = real_hyps
engine.framework._save()
print(f"  删除 {test_hyp_count} 个测试假设，保留 {len(real_hyps)} 个真实假设")
for h in real_hyps:
    print(f"    [{h['status']}] posterior={h['posterior']:.2f} evidence={h['evidence_count']} {h['statement'][:50]}")

# 3. 处理 confirmed 假设 → 生成知识条目
print()
print("[3] 处理 confirmed 假设...")
confirmed = [h for h in real_hyps if h.get("status") == "confirmed"]
print(f"  Confirmed 假设: {len(confirmed)}")
for h in confirmed:
    print(f"    {h['id']}: {h['statement'][:60]}")
    print(f"      posterior={h['posterior']:.2f} evidence={h['evidence_count']}")
    
    # 写入知识条目
    engine.writer.write(
        title=f"确认假设: {h['id']}",
        content=f"确认假设: {h['statement']} (posterior={h['posterior']:.2f}, evidence={h['evidence_count']})",
    )
    print(f"      → 知识条目已写入")

# 4. 生成刻意练习计划
print()
print("[4] 刻意练习计划...")
# 读取工具统计
stats_data = engine.tool_stats.load()
tools = stats_data.get("tools", {})

# 找低成功率工具（排除 deprecated）
weak_tools = []
for name, stats in tools.items():
    if stats.get("deprecated"):
        continue
    total = stats.get("total_calls", 0)
    success = stats.get("success_count", 0)
    if total >= 3:
        rate = success / total
        if rate < 0.7:
            weak_tools.append((name, rate, total, success))

# 找高成功率但低调用次数的工具（需要更多练习）
underused_tools = []
for name, stats in tools.items():
    if stats.get("deprecated"):
        continue
    total = stats.get("total_calls", 0)
    success = stats.get("success_count", 0)
    rate = success / total if total > 0 else 0
    if total < 5 and rate >= 0.7:
        underused_tools.append((name, rate, total))

print(f"  低成功率工具 ({len(weak_tools)}):")
for name, rate, total, success in weak_tools:
    print(f"    {name}: {rate:.1%} ({success}/{total})")
    # 生成练习建议
    suggestion = f"在下一次对话中，主动使用 {name} 工具，注意失败模式并尝试不同的参数组合"
    print(f"      练习: {suggestion}")

print(f"\n  低使用量工具 ({len(underused_tools)}):")
for name, rate, total in underused_tools[:5]:
    print(f"    {name}: {rate:.1%} ({total} calls)")

# 5. 保存练习计划
practice_plan = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "weak_tools": [{"name": n, "rate": r, "total": t, "success": s} for n, r, t, s in weak_tools],
    "underused_tools": [{"name": n, "rate": r, "total": t} for n, r, t in underused_tools[:5]],
    "confirmed_hypotheses": len(confirmed),
    "goal": "通过刻意练习提升低成功率工具的表现",
}

plan_path = Path.home() / ".TuringClaw" / "cognitive" / "practice_plan.json"
plan_path.write_text(json.dumps(practice_plan, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n  练习计划已保存: {plan_path}")

# 6. 导出更新后的 behavior_rules
print()
print("[5] 导出 behavior_rules...")
approved = engine.meta_rules.get_approved()
drafts = engine.meta_rules.get_drafts()
behavior_rules = []
for r in approved:
    behavior_rules.append({
        "id": r["id"], "trigger": r["trigger_pattern"], "rule": r["rule_text"],
        "confidence": r["confidence"], "status": r["status"], "action": "apply",
    })
for r in drafts:
    if r.get("confidence", 0) >= 0.8:
        behavior_rules.append({
            "id": r["id"], "trigger": r["trigger_pattern"], "rule": r["rule_text"],
            "confidence": r["confidence"], "status": "draft_high_confidence", "action": "suggest",
        })

rules_path = Path.home() / ".TuringClaw" / "cognitive" / "behavior_rules.json"
rules_path.write_text(json.dumps(behavior_rules, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"  导出 {len(behavior_rules)} 条规则")
for r in behavior_rules:
    print(f"    [{r['action']}] {r['trigger']}")

# 7. 最终状态
print()
print("=== 最终状态 ===")
print(f"  Rules: {len(real_rules)} ({len(approved)} approved, {len(drafts)} drafts)")
print(f"  Hypotheses: {len(real_hyps)} ({len(confirmed)} confirmed, {len(real_hyps) - len(confirmed)} active)")
print(f"  Practice plan: {len(weak_tools)} weak tools, {len(underused_tools[:5])} underused")
print(f"  Behavior rules: {len(behavior_rules)}")
