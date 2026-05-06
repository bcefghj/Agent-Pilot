#!/usr/bin/env python3
"""Test the full /pilot command flow on server."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

USER_OPEN_ID = "ou_c5df0f9713f22db137b066d509d81c39"

def test_pilot_doc():
    """Test: /pilot 帮我写一份关于人工智能发展的文档"""
    print("=== Test: /pilot 帮我写一份关于人工智能发展的文档 ===")
    from core.agent_pilot import service
    from core.container import register_defaults
    register_defaults()

    intent = "帮我写一份关于人工智能发展的文档"
    plan = service.launch(
        user_open_id=USER_OPEN_ID,
        intent=intent,
        meta={"auto_confirm": True},
    )
    print(f"Plan created: {plan.plan_id}")
    print(f"Steps: {len(plan.steps)}")
    for i, step in enumerate(plan.steps):
        print(f"  step[{i}]: tool={step.tool} desc={step.description[:50]}")

    time.sleep(2)
    plan_obj = service.get_plan(plan.plan_id)
    if plan_obj:
        print(f"\nPlan status: {plan_obj.status}")
        for i, step in enumerate(plan_obj.steps):
            print(f"  step[{i}]: status={step.status} result={str(step.result)[:80] if step.result else 'None'}")
    return plan

def test_pilot_ppt():
    """Test: /pilot 做个关于Agent-Pilot产品介绍的PPT"""
    print("\n=== Test: /pilot 做个关于Agent-Pilot的PPT ===")
    from core.agent_pilot import service
    intent = "做个关于Agent-Pilot产品功能介绍的PPT大纲"
    plan = service.launch(
        user_open_id=USER_OPEN_ID,
        intent=intent,
        meta={"auto_confirm": True},
    )
    print(f"Plan created: {plan.plan_id}")
    print(f"Steps: {len(plan.steps)}")
    for i, step in enumerate(plan.steps):
        print(f"  step[{i}]: tool={step.tool} desc={step.description[:50]}")
    return plan

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["doc", "ppt", "both"], default="doc")
    args = parser.parse_args()

    if args.test in ("doc", "both"):
        test_pilot_doc()
    if args.test in ("ppt", "both"):
        test_pilot_ppt()

    print("\n=== Waiting 15s for background tasks to complete ===")
    time.sleep(15)

    from core.agent_pilot import service
    plans = service.list_plans(USER_OPEN_ID)
    print(f"\nAll plans for user ({len(plans)} total):")
    for p in plans[-3:]:
        print(f"  plan={p.plan_id} status={p.status} intent={p.intent[:40]}")
        for s in p.steps:
            result_preview = str(s.result)[:60] if s.result else "None"
            print(f"    step: {s.tool} status={s.status} result={result_preview}")
