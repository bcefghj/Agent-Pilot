"""Surface 层基础测试 — 卡片构造 + Router + MCP server."""

from __future__ import annotations

import pytest


# ── Cards ────────────────────────────────────────────────────────────────────


def test_task_suggested_card_shape():
    from pilot.surface.feishu.cards import task_suggested_card

    card = task_suggested_card(
        task_id="task_xxx",
        title="测试任务",
        intent="帮我做个汇报",
        owner_display="ou123",
        plan_outline=["拉上下文", "生成文档", "生成 PPT"],
        context_state={"used": ["IM 5 条"], "missing": ["历史复盘"]},
    )
    assert card["header"]["template"] == "blue"
    actions = next(e for e in card["elements"] if e.get("tag") == "action")
    btn_actions = [a["value"]["action"] for a in actions["actions"]]
    # PRD §6 必须的 5 个按钮
    assert "pilot.task.confirm" in btn_actions
    assert "pilot.task.add_context" in btn_actions
    assert "pilot.task.assign" in btn_actions
    assert "pilot.task.claim" in btn_actions
    assert "pilot.task.ignore" in btn_actions


def test_context_confirm_card():
    from pilot.surface.feishu.cards import context_confirm_card

    card = context_confirm_card(
        task_id="t1",
        summary={"task_goal": "g1", "used": ["IM 10 条"], "missing": ["预算表"]},
    )
    actions = next(e for e in card["elements"] if e.get("tag") == "action")
    btns = [a["value"]["action"] for a in actions["actions"]]
    assert "pilot.ctx.confirm" in btns


def test_progress_card_has_streaming_anchor():
    from pilot.surface.feishu.cards import task_progress_card

    card = task_progress_card(task_id="t1", state="running", progress=0.42, current_step="生成文档")
    # 必须有 streaming 锚点 element_id
    md_elem = next(e for e in card["elements"] if e.get("tag") == "markdown")
    assert md_elem["element_id"]


# ── Router ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_router_clarify_button_routes_to_clarify_namespace():
    """v13 P0 修复验证：clarify 按钮统一到 pilot.clarify.* 命名空间."""
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    # 用户点击「生成 PPT」按钮
    res = await router.handle_card_action(
        actor_open_id="ou_user",
        action="pilot.clarify.choose",
        value={"choice": "ppt", "intent": "帮我做个汇报"},
    )
    # 修复后应该被 router 处理（不再 unknown_action）
    # plan_launcher 未注入时 verdict=ready
    assert res.handled
    assert res.verdict in ("ready", "error")


@pytest.mark.asyncio
async def test_router_clarify_skip():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_card_action(
        actor_open_id="ou_user",
        action="pilot.clarify.skip",
        value={"intent": "帮我做个汇报"},
    )
    assert res.handled


@pytest.mark.asyncio
async def test_router_help_command():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_message(
        sender_open_id="ou1",
        text="帮助",
        chat_id="oc1",
    )
    assert res.handled
    assert res.card is not None
    assert "Agent-Pilot V1" in res.card["header"]["title"]["content"]


@pytest.mark.asyncio
async def test_router_explicit_pilot():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_message(
        sender_open_id="ou1",
        text="/pilot 帮我写一份产品方案",
        chat_id="oc1",
    )
    assert res.handled
    # 没注入 plan_launcher 时回 text_reply
    assert res.text_reply
    assert "未注入" in res.text_reply or "已启动" in res.text_reply


@pytest.mark.asyncio
async def test_router_natural_language_clarify():
    """自然语言模糊意图触发澄清卡片."""
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_message(
        sender_open_id="ou1",
        text="帮我做个 PPT",
        chat_id="oc1",
    )
    # 信息不足应触发澄清
    assert res.handled
    assert res.verdict in ("clarify", "ready")


@pytest.mark.asyncio
async def test_router_pilot_confirm_button():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_card_action(
        actor_open_id="ou1",
        action="pilot.task.confirm",
        value={"task_id": "task_xx"},
    )
    assert res.handled
    assert res.verdict == "confirmed"


@pytest.mark.asyncio
async def test_router_pilot_ignore():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_card_action(
        actor_open_id="ou1",
        action="pilot.task.ignore",
        value={"task_id": "task_xx"},
    )
    assert res.handled
    assert res.verdict == "ignored"


@pytest.mark.asyncio
async def test_router_unknown_action_handled_gracefully():
    from pilot.surface.feishu.router import FeishuRouter

    router = FeishuRouter()
    res = await router.handle_card_action(
        actor_open_id="ou1",
        action="random.unknown.action",
        value={},
    )
    assert not res.handled
    assert "unknown_action" in res.error


# ── MCP Server ───────────────────────────────────────────────────────────────


def test_mcp_server_creates_app():
    from pilot.surface.mcp_server import create_app

    app = create_app()
    assert app.title.startswith("Agent-Pilot")
    routes = [r.path for r in app.routes]
    assert "/tools/list" in routes
    assert "/tools/call" in routes


# ── Dashboard FastAPI ────────────────────────────────────────────────────────


def test_dashboard_app_has_routes():
    from pilot.surface.dashboard.server import create_app

    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/" in routes
    assert "/dashboard" in routes
    assert "/multi-end" in routes
    assert "/api/sessions" in routes
    assert "/api/tools" in routes
    assert "/health" in routes
