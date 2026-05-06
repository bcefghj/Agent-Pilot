"""飞书 Interactive Card 构造器（v2 标准卡片 + CardKit 2.0 增强字段）."""

from __future__ import annotations

from typing import Any


def task_suggested_card(
    *,
    task_id: str,
    title: str,
    intent: str,
    owner_display: str = "",
    plan_outline: list[str] | None = None,
    context_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """PRD §5 任务卡片（建议执行/确认/指派/添加资料/忽略）."""
    elements = [
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": f"**🛫 Agent-Pilot · 任务建议**\n\n意图：{intent[:100]}"}},
        {"tag": "hr"},
    ]
    if plan_outline:
        outline_md = "\n".join(f"- {step}" for step in plan_outline[:6])
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": f"**计划概览**\n{outline_md}"}})
    if context_state:
        used = context_state.get("used", [])
        missing = context_state.get("missing", [])
        info = []
        if used:
            info.append(f"✅ 已用：{used if isinstance(used, str) else len(used)} 项")
        if missing:
            info.append(f"❓ 缺失：{', '.join(missing) if isinstance(missing, list) else missing}")
        if info:
            elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                    "content": "**上下文** · " + " · ".join(info)}})
    if owner_display:
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": f"**当前 owner**：{owner_display}"}})

    elements.append({"tag": "action", "actions": [
        _btn("✅ 确认执行", "pilot.task.confirm", task_id, primary=True),
        _btn("📎 添加资料", "pilot.task.add_context", task_id),
        _btn("👤 指派他人", "pilot.task.assign", task_id),
        _btn("✋ 我来执行", "pilot.task.claim", task_id),
        _btn("🙅 忽略", "pilot.task.ignore", task_id, danger=True),
    ]})

    return {
        "header": {"title": {"tag": "plain_text", "content": f"🛫 {title or 'Agent-Pilot 任务'}"},
                   "template": "blue"},
        "elements": elements,
    }


def context_confirm_card(
    *,
    task_id: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """PRD §7.2 上下文确认卡片."""
    used = summary.get("used", [])
    missing = summary.get("missing", [])
    elements = [
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": f"**📦 上下文确认**\n\n任务目标：{summary.get('task_goal', '')[:100]}"}},
        {"tag": "hr"},
    ]
    if used:
        used_md = "\n".join(f"- {u}" for u in used)
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**已用资料**\n{used_md}"}})
    if missing:
        missing_md = "\n".join(f"- {m}" for m in missing)
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**建议补充**\n{missing_md}"}})

    elements.append({"tag": "action", "actions": [
        _btn("✅ 确认上下文", "pilot.ctx.confirm", task_id, primary=True),
        _btn("📎 继续补充", "pilot.ctx.add_more", task_id),
        _btn("⏸ 暂停", "pilot.task.pause", task_id),
    ]})

    return {
        "header": {"title": {"tag": "plain_text", "content": "📦 上下文确认"}, "template": "indigo"},
        "elements": elements,
    }


def task_progress_card(
    *,
    task_id: str,
    title: str = "",
    state: str = "running",
    progress: float = 0.0,
    current_step: str = "",
    streaming_content: str = "",
    element_id: str = "stream_text",
) -> dict[str, Any]:
    """流式进度卡（CardKit 2.0 streaming 用，element_id 是 patch 锚点）."""
    pct = int(progress * 100)
    bar = "▓" * (pct // 5) + "░" * (20 - pct // 5)
    elements = [
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": f"**🛫 {title or 'Agent-Pilot 执行中'}**\n\n进度：`{bar}` {pct}%"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"当前步骤：{current_step}"}},
        {"tag": "hr"},
        {
            "tag": "markdown",
            "element_id": element_id,
            "content": streaming_content or "_等待 Agent 响应..._",
        },
    ]
    return {
        "header": {"title": {"tag": "plain_text", "content": f"🛫 {title or 'Agent-Pilot'}"}, "template": "turquoise"},
        "elements": elements,
    }


def task_delivered_card(
    *,
    task_id: str,
    title: str = "",
    artifacts: list[dict[str, Any]] | None = None,
    share_url: str = "",
) -> dict[str, Any]:
    """任务交付卡（PRD §F-13）."""
    elements = [
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": f"**🛬 任务完成**\n\n{title or '产物已生成'}"}},
        {"tag": "hr"},
    ]
    for a in (artifacts or [])[:6]:
        kind = a.get("kind", "")
        url = a.get("url", "") or a.get("uri", "")
        ttl = a.get("title", "")
        emoji = {"doc": "📄", "canvas": "🎨", "slide": "📊"}.get(kind, "📦")
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": f"{emoji} **{kind}** {ttl}：[{url}]({url})"}})
    if share_url:
        elements.append({"tag": "action", "actions": [
            {"tag": "button", "text": {"tag": "plain_text", "content": "🔗 打开分享链接"},
             "type": "primary", "url": share_url},
            _btn("📁 归档", "pilot.task.archive", task_id),
        ]})
    return {
        "header": {"title": {"tag": "plain_text", "content": "🛬 Agent-Pilot · 任务完成"}, "template": "green"},
        "elements": elements,
    }


def help_card() -> dict[str, Any]:
    return {
        "header": {"title": {"tag": "plain_text", "content": "🛫 Agent-Pilot V1 · 使用帮助"}, "template": "blue"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": (
                "**自然语言触发（最常用）**\n"
                "- `帮我写一份关于 X 的报告` → 文档\n"
                "- `做一份 8 页客户汇报 PPT` → PPT\n"
                "- `画一张产品架构图` → 画布\n"
                "- `产品方案 + 架构图 + 评审 PPT` → ⭐ 三件套\n\n"
                "**显式命令**\n"
                "- `/pilot <意图>` 强制触发\n"
                "- `状态` 查看进度\n"
                "- `帮助` 显示本卡片\n\n"
                "**模糊意图会主动澄清**：发`帮我做个汇报`试试 ✨"
            )}},
        ],
    }


def first_time_welcome_card() -> dict[str, Any]:
    return {
        "header": {"title": {"tag": "plain_text", "content": "👋 欢迎使用 Agent-Pilot V1"}, "template": "blue"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": (
                "你好！👋 我是 **Agent-Pilot V1**，飞书 IM 中的 AI 主驾驶。\n\n"
                "我可以把你的「群聊讨论 → 文档 → 画布 → PPT + 演讲稿」压缩到 **90 秒** 一键交付。\n\n"
                "试试用自然语言告诉我你要做什么："
            )}},
            {"tag": "div", "text": {"tag": "lark_md", "content": (
                "- 📄 `帮我写一份 AI Agent 趋势报告`\n"
                "- 📊 `做一份 8 页客户汇报 PPT`\n"
                "- 🎨 `画一张产品架构图`\n"
                "- ⭐ `产品方案 + 架构图 + 评审 PPT 三件套`"
            )}},
            {"tag": "action", "actions": [
                {"tag": "button", "text": {"tag": "plain_text", "content": "📖 查看帮助"},
                 "value": {"action": "pilot.help"}, "type": "primary"},
            ]},
        ],
    }


# ── helpers ──


def _btn(label: str, action: str, task_id: str, *, primary: bool = False, danger: bool = False) -> dict[str, Any]:
    btn: dict[str, Any] = {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "value": {"action": action, "task_id": task_id},
    }
    if primary:
        btn["type"] = "primary"
    elif danger:
        btn["type"] = "danger"
    return btn
