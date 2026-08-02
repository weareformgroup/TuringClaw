# -*- coding: utf-8 -*-
"""
GSM Evolution Validator — 检查系统是否在自我进化

验证指标:
1. Layer 4: intuitions 数量是否增长
2. Layer 3: 是否有规则草稿被创建
3. Layer 2: 是否有假设被创建/更新
4. GBrain: cognitive_summary page 是否存在且更新
5. Linkage: 联动事件是否发生
6. brain_score: 是否有变化
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, r"C:\Users\Administrator")
sys.path.insert(0, r"C:\Users\Administrator\TuringClaw2.0")

from cognitive.dual_spiral_engine import DualSpiralEngine


def validate_evolution():
    """检查系统自我进化状态。"""
    print("=" * 60)
    print("GSM Evolution Validator")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    engine = DualSpiralEngine()
    status = engine.status()

    # Layer 4
    print("\n[Layer 4 - Tacit]")
    intuitions = engine.intuition.load().get("intuitions", [])
    tools = engine.tool_stats.load().get("tools", {})
    print(f"  Intuitions: {len(intuitions)}")
    print(f"  Tools tracked: {len(tools)}")
    
    # 检查有 evidence 的直觉
    with_evidence = [i for i in intuitions if i.get("evidence_count", 0) > 0]
    with_high_evidence = [i for i in intuitions if i.get("evidence_count", 0) >= 3]
    print(f"  With evidence: {len(with_evidence)}")
    print(f"  With high evidence (>=3): {len(with_high_evidence)}")
    
    for i in with_high_evidence[:5]:
        trigger = i.get("trigger", "?")
        count = i.get("evidence_count", 0)
        action = i.get("learned_action", "")[:50]
        print(f"    [{count}x] {trigger} → {action}")

    # Layer 3
    print("\n[Layer 3 - Meta-Rules]")
    l3 = status["layer3_metarules"]
    print(f"  Total: {l3['total']}")
    print(f"  Drafts: {l3['draft']}")
    print(f"  Approved: {l3['approved']}")
    print(f"  Avg effectiveness: {l3['avg_effectiveness']:.2f}")

    drafts = engine.meta_rules.get_drafts()
    for d in drafts[:5]:
        print(f"    DRAFT: {d['rule_text'][:60]}")

    # Layer 2
    print("\n[Layer 2 - Framework]")
    l2 = status["layer2_framework"]
    print(f"  Total: {l2['total']}")
    print(f"  Active: {l2['active']}")
    print(f"  Confirmed: {l2['confirmed']}")
    print(f"  Deprecated: {l2['deprecated']}")
    print(f"  Avg confidence: {l2['avg_confidence']:.2f}")

    needs_reflection = engine.framework.needs_reflection()
    for h in needs_reflection[:5]:
        print(f"    REFLECT: '{h['statement'][:50]}' posterior={h['posterior']:.2f}")

    # Linkage
    print("\n[Linkage]")
    ll = status["linkage"]
    print(f"  Total events: {ll['linkage_events']}")
    print(f"  L4→L3: {ll['l4_to_l3']}")
    print(f"  L4→L2: {ll['l4_to_l2']}")
    print(f"  L3→L2: {ll['l3_to_l2']}")
    print(f"  L2→L1: {ll['l2_to_l1']}")
    print(f"  L1→L4: {ll['l1_to_l4']}")

    # Cognitive summary
    print("\n[Cognitive Summary]")
    summary_path = Path.home() / ".TuringClaw" / "cognitive" / "cognitive_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"  Last cycle: {summary.get('timestamp', '?')}")
        print(f"  Last cycle new drafts: {summary.get('layer3', {}).get('new_drafts_this_cycle', 0)}")
        print(f"  Last cycle new hypotheses: {summary.get('layer2', {}).get('new_hypotheses_this_cycle', 0)}")
    else:
        print("  No cognitive summary found (cognitive cycle not run yet)")

    # GBrain check
    print("\n[GBrain]")
    try:
        from gui.brain_client import BrainClient
        bc = BrainClient()
        if bc.is_available():
            stats = bc.get_stats()
            if stats:
                print(f"  Brain stats: {stats}")
            # Check for cognitive cycle page
            page = bc.get_page("concepts/gsm-cognitive-cycle")
            if page:
                print(f"  Cognitive cycle page: EXISTS")
            else:
                print(f"  Cognitive cycle page: NOT FOUND")
        else:
            print("  GBrain not available")
    except Exception as e:
        print(f"  GBrain check failed: {e}")

    # Evolution verdict
    print("\n" + "=" * 60)
    print("EVOLUTION VERDICT")
    print("=" * 60)
    
    signals = []
    if len(intuitions) > 0:
        signals.append(f"Layer 4 accumulating ({len(intuitions)} intuitions)")
    if l3["draft"] > 0:
        signals.append(f"Layer 3 creating drafts ({l3['draft']})")
    if l2["total"] > 0:
        signals.append(f"Layer 2 creating hypotheses ({l2['total']})")
    if ll["linkage_events"] > 0:
        signals.append(f"Linkage active ({ll['linkage_events']} events)")
    if summary_path.exists():
        signals.append("Cognitive cycle running")

    if len(signals) >= 3:
        print(f"  STATUS: EVOLVING ({len(signals)}/5 signals)")
    elif len(signals) >= 1:
        print(f"  STATUS: STARTING ({len(signals)}/5 signals)")
    else:
        print(f"  STATUS: DORMANT ({len(signals)}/5 signals)")
    
    for s in signals:
        print(f"  + {s}")
    
    print()


if __name__ == "__main__":
    validate_evolution()
