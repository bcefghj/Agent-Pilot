"""飞书消息 + 卡片回调统一路由.

修复 v13 P0 Bug：澄清卡按钮 `clarify_answer/clarify_skip` 失效的问题
→ 统一到 `pilot.clarify.*` 命名空间，单一 router 处理所有 pilot.* action。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pilot.capability.workforce.clarifier import Clarifier
from pilot.runtime.intent_router import (
    ChatMessage,
    IntentRouter,
    IntentVerdict,
)
from pilot.runtime.session import Session, Task

logger = logging.getLogger("pilot.surface.feishu.router")


@dataclass
class RouterResult:
    handled: bool = False
    verdict: str = ""
    task_id: str = ""
    card: dict[str, Any] | None = None
    next_action: str = ""
    text_reply: str = ""
    error: str = ""


# 启动 plan 的回调签名
PlanLauncher = Callable[..., Awaitable[dict[str, Any]]]


class FeishuRouter:
    """单一入口路由：消息 → 三闸门 → 创建任务 / 澄清 / 直接执行 ."""

    def __init__(
        self,
        *,
        intent_router: IntentRouter | None = None,
        clarifier: Clarifier | None = None,
        plan_launcher: PlanLauncher | None = None,
    ) -> None:
        self.intent_router = intent_router or IntentRouter()
        self.clarifier = clarifier or Clarifier()
        self.plan_launcher = plan_launcher
        self._recent: dict[str, list[ChatMessage]] = {}
        self._max_recent = 30
        self._sessions: dict[str, Session] = {}  # chat_id -> Session

    # ── 文本消息入口 ──
    async def handle_message(
        self,
        *,
        sender_open_id: str,
        text: str,
        chat_id: str = "",
        msg_id: str = "",
        is_explicit: bool = False,
    ) -> RouterResult:
        """处理一条 IM 文本消息."""
        text = (text or "").strip()
        if not text:
            return RouterResult(handled=False, verdict="empty")

        chat_id = chat_id or sender_open_id

        # 命令路径
        if text.lower() in ("帮助", "/help", "help"):
            from pilot.surface.feishu.cards import help_card
            return RouterResult(handled=True, verdict="help_command", card=help_card())

        if text.lower() in ("状态", "status", "/status"):
            return RouterResult(handled=True, verdict="status",
                                text_reply="当前没有正在执行的任务（V1 简化版）")

        # 累积上下文
        msg = ChatMessage(sender_open_id=sender_open_id, text=text, chat_id=chat_id, msg_id=msg_id, ts=int(time.time()))
        buf = self._recent.setdefault(chat_id, [])
        buf.append(msg)
        if len(buf) > self._max_recent:
            del buf[: len(buf) - self._max_recent]

        # 显式触发
        if is_explicit or text.lower().startswith(("/pilot", "@pilot")):
            return await self._launch(intent=_strip_prefix(text), chat_id=chat_id, sender_open_id=sender_open_id)

        # 三闸门
        result = await self.intent_router.detect(buf)

        if result.verdict == IntentVerdict.NOT_INTENT:
            return RouterResult(handled=False, verdict="not_intent")

        if result.verdict in (IntentVerdict.COOLDOWN, IntentVerdict.IGNORED):
            return RouterResult(handled=True, verdict=result.verdict.value, next_action="silent")

        if result.verdict == IntentVerdict.NEEDS_CLARIFY:
            req = self.clarifier.build_request(intent=text, questions=result.clarify_questions)
            return RouterResult(handled=True, verdict="clarify", card=req.to_card(),
                                next_action="awaiting_user_clarify_answer")

        # READY
        return await self._launch(intent=text, chat_id=chat_id, sender_open_id=sender_open_id)

    # ── 卡片回调入口 ──
    async def handle_card_action(
        self,
        *,
        actor_open_id: str,
        action: str,
        value: dict[str, Any],
    ) -> RouterResult:
        """处理飞书卡片按钮回调."""
        if not action:
            return RouterResult(handled=False, error="empty_action")

        # 修复 v13 P0：clarify 按钮路由
        if action == "pilot.clarify.choose":
            choice = value.get("choice", "doc")
            intent = value.get("intent", "")
            expanded = self.clarifier.expand_choice(intent=intent, choice=choice)
            return await self._launch(intent=expanded, chat_id=actor_open_id, sender_open_id=actor_open_id)

        if action == "pilot.clarify.skip":
            intent = value.get("intent", "") or "Agent-Pilot 任务"
            return await self._launch(intent=intent, chat_id=actor_open_id, sender_open_id=actor_open_id)

        # PRD §6 owner 流转 + §F-10 指派
        if action == "pilot.task.confirm":
            return RouterResult(handled=True, verdict="confirmed", task_id=value.get("task_id", ""),
                                next_action="orchestrator_running",
                                text_reply="✅ 已确认，开始执行")

        if action == "pilot.task.ignore":
            return RouterResult(handled=True, verdict="ignored", task_id=value.get("task_id", ""),
                                text_reply="🙅 已忽略本次建议")

        if action == "pilot.task.assign":
            return RouterResult(handled=True, verdict="assign_pending", task_id=value.get("task_id", ""),
                                text_reply="👤 请 @ 一位群成员，回复 `指派 @某人` 完成转交")

        if action == "pilot.task.claim":
            return RouterResult(handled=True, verdict="claimed", task_id=value.get("task_id", ""),
                                text_reply=f"✋ 已由 {actor_open_id[-6:]} 接管")

        if action == "pilot.task.add_context":
            return RouterResult(handled=True, verdict="add_context", task_id=value.get("task_id", ""),
                                text_reply="📎 请直接发送补充资料的链接或文件，我会自动拼到上下文包")

        if action == "pilot.task.archive":
            return RouterResult(handled=True, verdict="archived", task_id=value.get("task_id", ""),
                                text_reply="📁 已归档")

        if action == "pilot.task.pause":
            return RouterResult(handled=True, verdict="paused", task_id=value.get("task_id", ""),
                                text_reply="⏸ 已暂停，发送 `继续` 恢复")

        if action == "pilot.ctx.confirm":
            return RouterResult(handled=True, verdict="ctx_confirmed", task_id=value.get("task_id", ""),
                                text_reply="✅ 上下文已确认，正在生成产物...")

        if action == "pilot.help":
            from pilot.surface.feishu.cards import help_card
            return RouterResult(handled=True, verdict="help", card=help_card())

        return RouterResult(handled=False, error=f"unknown_action: {action}")

    # ── 内部 ──
    async def _launch(
        self,
        *,
        intent: str,
        chat_id: str,
        sender_open_id: str,
    ) -> RouterResult:
        if self.plan_launcher is None:
            return RouterResult(handled=True, verdict="ready", text_reply=f"🛫 收到意图：{intent[:60]}\n（V1 plan launcher 未注入）")

        try:
            res = await self.plan_launcher(
                intent=intent, chat_id=chat_id, sender_open_id=sender_open_id,
            )
            return RouterResult(
                handled=True,
                verdict="ready",
                task_id=res.get("plan_id", ""),
                text_reply=res.get("ack_text", f"🛫 已启动 Agent-Pilot · {intent[:30]}"),
                card=res.get("card"),
            )
        except Exception as e:
            logger.exception("launch failed: %s", e)
            return RouterResult(handled=True, verdict="error", text_reply=f"❌ 启动失败: {e}", error=str(e))


def _strip_prefix(text: str) -> str:
    text = text.strip()
    for p in ("/pilot", "@pilot", "/Pilot", "@Pilot"):
        if text.lower().startswith(p.lower()):
            return text[len(p):].strip(":：、 ").strip()
    return text
