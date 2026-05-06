"""5 条裁判级 e2e 用例.

每条用例对应 JUDGE_GUIDE.md 中的一个 30-second 验收点，
全部用 mocked LLM 在 30 秒内跑完。

1. test_short_doc          : 文档生成
2. test_three_in_one       : 文档 + 画布 + PPT 三件套
3. test_clarify_flow       : 模糊意图触发主动澄清（修复 v13 P0 BUG）
4. test_multi_end_event    : 多端 event log 一致性
5. test_voice_input_flow   : 语音输入 → 文本 → plan
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """每个用例独立数据目录 + 禁用飞书/真 LLM."""
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("DATA_DIR", d)
        monkeypatch.setenv("FEISHU_APP_ID", "cli_your_app_id_here")
        monkeypatch.setenv("FEISHU_APP_SECRET", "")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("DOUBAO_API_KEY", raising=False)
        # 重新加载需要 DATA_DIR 的模块
        import importlib
        from pilot.context import event_log, filesystem_memory
        from pilot.governance import audit
        importlib.reload(event_log)
        importlib.reload(filesystem_memory)
        importlib.reload(audit)
        yield Path(d)


# ── 1. 文档生成 ──────────────────────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_short_doc(setup_env):
    from pilot.capability.tools.registry import default_registry
    from pilot.runtime.orchestrator import Orchestrator
    from pilot.runtime.planner import plan_from_intent

    plan = plan_from_intent("帮我写一份关于 AI Agent 发展趋势的报告")
    reg = default_registry()
    orch = Orchestrator(reg)
    summary = await orch.run(plan)

    assert summary["completed"], "无步骤完成"
    # 必须有 doc.create + doc.append + archive.bundle
    tools = [s.tool for s in plan.steps]
    assert "doc.create" in tools
    assert "doc.append" in tools
    assert tools[-1] == "archive.bundle"

    # archive 必须收到 doc 的产物
    archive = next(s for s in plan.steps if s.tool == "archive.bundle")
    assert archive.result.get("ok"), "archive 未成功"
    assert archive.result.get("items_count", 0) >= 1, "归档未收到产物"


# ── 2. 三件套 ────────────────────────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_three_in_one(setup_env):
    from pilot.capability.tools.registry import default_registry
    from pilot.runtime.orchestrator import Orchestrator
    from pilot.runtime.planner import plan_from_intent

    plan = plan_from_intent("产品方案 + 架构图 + 评审 PPT")
    reg = default_registry()
    orch = Orchestrator(reg)
    summary = await orch.run(plan)

    tools = [s.tool for s in plan.steps]
    assert "doc.create" in tools
    assert "canvas.create" in tools
    assert "slide.generate" in tools

    # 三件套全部完成
    completed = set(summary["completed"])
    doc_steps = [s.step_id for s in plan.steps if s.tool == "doc.create"]
    canvas_steps = [s.step_id for s in plan.steps if s.tool == "canvas.create"]
    slide_steps = [s.step_id for s in plan.steps if s.tool == "slide.generate"]
    assert all(sid in completed for sid in doc_steps)
    assert all(sid in completed for sid in canvas_steps)
    assert all(sid in completed for sid in slide_steps)

    # 验证每个产出物都有 url / 文件
    for s in plan.steps:
        if s.tool == "doc.create":
            assert s.result.get("doc_token") and s.result.get("url"), "doc 缺 url"
        if s.tool == "canvas.create":
            assert s.result.get("canvas_id") and s.result.get("mermaid"), "canvas 缺 mermaid"
        if s.tool == "slide.generate":
            assert s.result.get("slide_id") and s.result.get("pages", 0) >= 5, "slide 页数不足"
            # 验证 .pptx 文件存在
            pptx_path = Path(s.result.get("pptx_path", ""))
            md_fallback = pptx_path.with_suffix(".md")
            assert pptx_path.exists() or md_fallback.exists(), "未生成 pptx 或 fallback md"


# ── 3. 澄清流程（修复 v13 P0 BUG）────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_clarify_flow(setup_env):
    """模糊意图 → 弹澄清卡 → 用户点按钮 → 重新规划."""
    from pilot.surface.feishu.router import FeishuRouter

    captured = {}

    async def fake_launcher(*, intent, chat_id, sender_open_id):
        captured["intent"] = intent
        captured["chat_id"] = chat_id
        return {"plan_id": "plan_test", "ack_text": f"启动 {intent}"}

    router = FeishuRouter(plan_launcher=fake_launcher)

    # Step 1: 模糊意图
    res = await router.handle_message(
        sender_open_id="ou1",
        text="帮我做个汇报",
        chat_id="oc1",
    )
    # 应当弹澄清卡
    assert res.handled
    assert res.verdict == "clarify"
    assert res.card is not None

    # 验证按钮的 action 全部用 pilot.clarify.* 命名空间
    actions = next(e for e in res.card["elements"] if e.get("tag") == "action")
    btn_actions = [a["value"]["action"] for a in actions["actions"]]
    assert all(a.startswith("pilot.clarify.") for a in btn_actions), \
        f"v13 P0 修复失效：按钮 action 应统一为 pilot.clarify.*，实际：{btn_actions}"

    # Step 2: 用户点击「文档 + PPT 三件套」
    res2 = await router.handle_card_action(
        actor_open_id="ou1",
        action="pilot.clarify.choose",
        value={"choice": "trio", "intent": "帮我做个汇报"},
    )
    assert res2.handled
    assert res2.verdict == "ready"
    assert "三件套" in captured["intent"], f"choice=trio 应展开为含'三件套'的意图，实际: {captured['intent']}"


# ── 4. 多端 event log 一致性 ────────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_multi_end_event_consistency(setup_env):
    """同一 session_id 在多个 EventLog 实例上读到的事件应一致（CRDT 基础保证）."""
    from pilot.context.event_log import EventLog

    sid = "sess_multi_end_test"
    log_a = EventLog(sid)
    log_b = EventLog(sid)

    # 模拟三端写
    await log_a.append("user_message", {"text": "from device A"})
    await log_b.append("user_message", {"text": "from device B"})
    await log_a.append("assistant_text", {"text": "回复"})

    # 各端读到的应一致（同一文件）
    a_events = log_a.read_all()
    b_events = log_b.read_all()
    assert len(a_events) == len(b_events)
    assert [e["payload"].get("text") for e in a_events] == [e["payload"].get("text") for e in b_events]


# ── 5. 语音输入 ──────────────────────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_voice_input_flow(setup_env, monkeypatch):
    """语音转写工具调用链路（mocked ASR）."""
    from pilot.capability.tools.registry import default_registry

    reg = default_registry()
    out = await reg.execute(
        tool_name="voice.transcribe",
        tool_input={"file_key": "fk_xxx", "message_id": "om_xxx"},
        ctx={},
    )
    # 没飞书 token 时 mock；至少返回 dict
    assert isinstance(out, dict)
    assert "text" in out


# ── 6. Workforce 三 Agent harness 端到端 ────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_workforce_three_agent_e2e(setup_env):
    """三 Agent harness 完整跑通三件套."""
    from pilot.capability.tools.registry import default_registry
    from pilot.capability.workforce.harness import WorkforceHarness

    reg = default_registry()
    wh = WorkforceHarness()
    result = await wh.run(intent="产品方案 + 架构图 + 评审 PPT", tool_executor=reg)

    assert result.spec.title
    assert len(result.sprints) >= 1
    assert result.artifacts  # 至少 1 个产物
    # 至少一个 sprint 评分通过
    passing = [s for s in result.sprints if s.score and s.score.is_passing()]
    assert passing, f"所有 sprint 评分都未通过: {[s.score.to_dict() if s.score else None for s in result.sprints]}"


# ── 性能门控（裁判演示稳定性）────────────────────────────────────────────────


@pytest.mark.competition
@pytest.mark.asyncio
async def test_three_in_one_under_30s(setup_env):
    """三件套必须在 mocked LLM 下 30 秒内完成（验收硬指标）."""
    import time

    from pilot.capability.tools.registry import default_registry
    from pilot.runtime.orchestrator import Orchestrator
    from pilot.runtime.planner import plan_from_intent

    plan = plan_from_intent("产品方案 + 架构图 + 评审 PPT")
    reg = default_registry()
    orch = Orchestrator(reg)

    t0 = time.monotonic()
    summary = await orch.run(plan)
    elapsed = time.monotonic() - t0

    assert elapsed < 30.0, f"三件套耗时 {elapsed:.1f}s 超过 30s 门控"
    assert len(summary["completed"]) == len(plan.steps), "存在未完成步骤"
