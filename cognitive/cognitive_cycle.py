# -*- coding: utf-8 -*-
"""
GSM Cognitive Cycle — 夜间认知循环

在 GBrain dream cycle 之后执行，触发 GSM 四层结晶更新：
1. 读取 Layer 4 统计数据（工具使用、执行直觉）
2. 检查是否有需要创建的 Layer 3 规则草稿
3. 检查 Layer 2 假设是否需要更新
4. 将关键发现同步写入 GBrain
5. 生成认知摘要
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Setup paths
TC_ROOT = Path(r"C:\Users\Administrator\TuringClaw2.0")
sys.path.insert(0, str(TC_ROOT))
sys.path.insert(0, str(TC_ROOT.parent))

from cognitive.dual_spiral_engine import DualSpiralEngine
from cognitive.layer2_framework.bayesian_updater import FrameworkUpdater
from cognitive.layer3_metarules.rules_manager import MetaRulesManager
from cognitive.crystallization_linkage import CrystallizationLinkage


def run_cognitive_cycle():
    """执行 GSM 夜间认知循环。"""
    print("=" * 60)
    print("GSM Cognitive Cycle - Nightly Reflection")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # 初始化组件
    engine = DualSpiralEngine()
    framework = engine.framework
    meta_rules = engine.meta_rules
    linkage = engine.linkage

    # Step 1: 读取 Layer 4 统计
    print("\n[1] Reading Layer 4 statistics...")
    intuitions = engine.intuition.load().get("intuitions", [])
    tool_stats = engine.tool_stats.load()
    tools = tool_stats.get("tools", {})

    print(f"  Intuitions: {len(intuitions)}")
    print(f"  Tools tracked: {len(tools)}")
    
    # 统计成功率
    low_success_tools = []
    for tool_name, stats in tools.items():
        total = stats.get("total_calls", 0)
        success = stats.get("success_count", 0)
        if total >= 3:
            rate = success / total
            if rate < 0.7:
                low_success_tools.append((tool_name, rate, total, success))
                print(f"  LOW SUCCESS: {tool_name} = {rate:.1%} ({success}/{total})")

    # Step 2: 检查 Layer 4 → Layer 3 联动（失败模式 → 规则草稿）
    print("\n[2] Checking L4→L3 linkage (failure patterns → rule drafts)...")
    new_drafts = 0
    for intu in intuitions:
        trigger = intu.get("trigger", "")
        evidence_count = intu.get("evidence_count", 0)
        learned = intu.get("learned_action", "")
        
        if evidence_count >= 3 and learned:
            # 检查是否已有规则
            existing = meta_rules.get_drafts() + meta_rules.get_approved()
            has_rule = any(trigger in r.get("trigger_pattern", "") for r in existing)
            
            if not has_rule:
                rule_text = f"当遇到 '{trigger}' 时，{learned}"
                meta_rules.create_draft(
                    trigger_pattern=trigger,
                    rule_text=rule_text,
                    source="tacit",
                    evidence_trigger=trigger,
                    confidence=min(0.8, 0.3 + 0.1 * evidence_count),
                )
                new_drafts += 1
                print(f"  Created draft: {rule_text}")

    print(f"  New rule drafts: {new_drafts}")

    # Step 3: 检查 Layer 2 假设状态
    print("\n[3] Checking Layer 2 hypotheses...")
    active_hyps = framework.get_active()
    deprecated = framework.get_deprecated()
    confirmed = framework.get_confirmed()
    needs_reflection = framework.needs_reflection()

    print(f"  Active: {len(active_hyps)}")
    print(f"  Confirmed: {len(confirmed)}")
    print(f"  Deprecated: {len(deprecated)}")
    print(f"  Needs reflection (posterior<0.3): {len(needs_reflection)}")

    for hyp in needs_reflection:
        print(f"  REFLECT: '{hyp['statement']}' posterior={hyp['posterior']:.2f}")

    # Step 4: 低成功率工具 → 创建假设
    print("\n[4] Creating hypotheses for low-success tools...")
    new_hyps = 0
    for tool_name, rate, total, success in low_success_tools:
        existing = framework.get_by_tag(tool_name)
        if not existing:
            framework.add_hypothesis(
                statement=f"{tool_name} 工具可靠性低 (success_rate={rate:.1%})",
                prior=0.3,
                tags=[tool_name, "reliability", "auto_generated"],
            )
            new_hyps += 1
            print(f"  Created hypothesis: {tool_name} reliability ({rate:.1%})")

    print(f"  New hypotheses: {new_hyps}")

    # Step 5: 生成认知摘要
    print("\n[5] Generating cognitive summary...")
    status = engine.status()
    
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "layer4": {
            "intuitions": len(intuitions),
            "tools_tracked": len(tools),
            "low_success_tools": len(low_success_tools),
        },
        "layer3": {
            "total_rules": status["layer3_metarules"]["total"],
            "drafts": status["layer3_metarules"]["draft"],
            "approved": status["layer3_metarules"]["approved"],
            "new_drafts_this_cycle": new_drafts,
        },
        "layer2": {
            "total_hypotheses": status["layer2_framework"]["total"],
            "active": status["layer2_framework"]["active"],
            "confirmed": status["layer2_framework"]["confirmed"],
            "deprecated": status["layer2_framework"]["deprecated"],
            "needs_reflection": len(needs_reflection),
            "new_hypotheses_this_cycle": new_hyps,
        },
        "linkage": status["linkage"],
    }

    # 保存摘要
    summary_path = Path.home() / ".TuringClaw" / "cognitive" / "cognitive_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"  Summary saved to: {summary_path}")
    print(f"  Layer 4: {len(intuitions)} intuitions, {len(low_success_tools)} low-success tools")
    print(f"  Layer 3: {new_drafts} new drafts, {status['layer3_metarules']['approved']} approved")
    print(f"  Layer 2: {new_hyps} new hypotheses, {len(needs_reflection)} need reflection")
    print(f"  Linkage events: {status['linkage']['linkage_events']} total")

    # Step 6: 同步关键发现到 GBrain（如果可用）
    print("\n[6] Syncing key findings to GBrain...")
    try:
        from gui.brain_client import BrainClient
        bc = BrainClient()
        if bc.is_available():
            # 写入认知摘要 page
            brain_body = f"# GSM Cognitive Cycle Summary\n\n"
            brain_body += f"Generated: {summary['timestamp']}\n\n"
            brain_body += f"## Layer 4 (Tacit)\n"
            brain_body += f"- Intuitions: {len(intuitions)}\n"
            brain_body += f"- Low success tools: {', '.join(t[0] for t in low_success_tools) if low_success_tools else 'none'}\n\n"
            brain_body += f"## Layer 3 (Meta-Rules)\n"
            brain_body += f"- New drafts: {new_drafts}\n"
            brain_body += f"- Total approved: {status['layer3_metarules']['approved']}\n\n"
            brain_body += f"## Layer 2 (Framework)\n"
            brain_body += f"- Needs reflection: {len(needs_reflection)}\n"
            for hyp in needs_reflection:
                brain_body += f"  - '{hyp['statement']}' (posterior={hyp['posterior']:.2f})\n"
            
            bc.put_page(
                slug="concepts/gsm-cognitive-cycle",
                body=brain_body,
                page_type="concept",
            )
            print("  Synced to GBrain: concepts/gsm-cognitive-cycle")
        else:
            print("  GBrain not available, skipping sync")
    except Exception as e:
        print(f"  GBrain sync failed: {e}")

    print("\n" + "=" * 60)
    print("GSM Cognitive Cycle Complete")
    print("=" * 60)
    
    return summary


if __name__ == "__main__":
    summary = run_cognitive_cycle()
    print(f"\nResult: {json.dumps(summary, ensure_ascii=False, indent=2)}")
