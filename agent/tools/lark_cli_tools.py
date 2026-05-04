"""Lark CLI Tools · 封装 @larksuite/cli 24 个 AI Agent Skill.

通过 subprocess 调用已安装的 lark-cli 命令，为 Agent 提供
飞书全平台操作能力。每个工具都有 graceful fallback。

Ref: https://github.com/larksuite/cli
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from .registry import tool

logger = logging.getLogger("agent.tools.lark_cli")

_CLI_BIN = None


def _find_cli() -> Optional[str]:
    global _CLI_BIN
    if _CLI_BIN is not None:
        return _CLI_BIN or None
    for name in ("lark-cli", "lark"):
        path = shutil.which(name)
        if path:
            _CLI_BIN = path
            return path
    _CLI_BIN = ""
    return None


def _run_cli(args: List[str], timeout: int = 30) -> Optional[Dict[str, Any]]:
    cli = _find_cli()
    if not cli:
        return None
    try:
        result = subprocess.run(
            [cli, *args, "--output", "json"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"raw": result.stdout.strip()}
        logger.debug("lark-cli %s failed: %s", args[0], result.stderr[:200])
        return None
    except subprocess.TimeoutExpired:
        logger.warning("lark-cli %s timed out after %ds", args[0], timeout)
        return None
    except Exception as e:
        logger.debug("lark-cli error: %s", e)
        return None


@tool(
    name="lark.docs.create",
    description="通过飞书 CLI 创建文档",
    permission="write",
    team="any",
)
def cli_docs_create(title: str = "", content: str = "", folder: str = "") -> Dict[str, Any]:
    args = ["docs", "create", "--title", title or "Agent-Pilot Doc"]
    if content:
        args.extend(["--content", content[:10000]])
    if folder:
        args.extend(["--folder", folder])
    result = _run_cli(args, timeout=30)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli not available or command failed"}


@tool(
    name="lark.docs.read",
    description="通过飞书 CLI 读取文档内容",
    permission="readonly",
    team="any",
)
def cli_docs_read(url: str = "", doc_id: str = "") -> Dict[str, Any]:
    args = ["docs", "read"]
    if url:
        args.extend(["--url", url])
    elif doc_id:
        args.extend(["--id", doc_id])
    else:
        return {"ok": False, "error": "url or doc_id required"}
    result = _run_cli(args, timeout=30)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli read failed"}


@tool(
    name="lark.messenger.send",
    description="通过飞书 CLI 发送消息",
    permission="write",
    team="any",
)
def cli_messenger_send(chat_id: str = "", text: str = "", msg_type: str = "text") -> Dict[str, Any]:
    if not chat_id or not text:
        return {"ok": False, "error": "chat_id and text required"}
    args = ["messenger", "send", "--chat-id", chat_id, "--text", text[:5000]]
    if msg_type != "text":
        args.extend(["--type", msg_type])
    result = _run_cli(args, timeout=15)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli send failed"}


@tool(
    name="lark.sheets.read",
    description="通过飞书 CLI 读取表格数据",
    permission="readonly",
    team="any",
)
def cli_sheets_read(url: str = "", sheet_id: str = "", range: str = "") -> Dict[str, Any]:
    args = ["sheets", "read"]
    if url:
        args.extend(["--url", url])
    elif sheet_id:
        args.extend(["--id", sheet_id])
    else:
        return {"ok": False, "error": "url or sheet_id required"}
    if range:
        args.extend(["--range", range])
    result = _run_cli(args, timeout=30)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli sheets read failed"}


@tool(
    name="lark.calendar.list",
    description="通过飞书 CLI 查看日历事件",
    permission="readonly",
    team="any",
)
def cli_calendar_list(days: int = 7) -> Dict[str, Any]:
    args = ["calendar", "list", "--days", str(days)]
    result = _run_cli(args, timeout=15)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli calendar failed"}


@tool(
    name="lark.tasks.create",
    description="通过飞书 CLI 创建任务",
    permission="write",
    team="any",
)
def cli_tasks_create(title: str = "", due: str = "", assignee: str = "") -> Dict[str, Any]:
    if not title:
        return {"ok": False, "error": "title required"}
    args = ["tasks", "create", "--title", title]
    if due:
        args.extend(["--due", due])
    if assignee:
        args.extend(["--assignee", assignee])
    result = _run_cli(args, timeout=15)
    if result:
        return {"ok": True, "provider": "lark-cli", **result}
    return {"ok": False, "error": "lark-cli tasks create failed"}


def cli_available() -> bool:
    return _find_cli() is not None
