"""Agent-Pilot V1 主入口.

用法:
    python -m pilot bot           # 只启飞书机器人长连接
    python -m pilot dashboard     # 只启 FastAPI Dashboard
    python -m pilot all           # 同时启动 bot + dashboard + sync hub + mcp
    python -m pilot mcp           # 只启 MCP server（供 Cursor / Claude 调用）
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# 配置日志（优先 structlog，回落到 std logging）
try:
    import structlog

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )
except ImportError:
    pass

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pilot")


BANNER = r"""
    ╔══════════════════════════════════════════════════════════╗
    ║  Agent-Pilot V1 · 飞书 IM 中的 AI 主驾驶 Harness          ║
    ║  飞书 AI 校园挑战赛 · 5 层 Harness 架构                    ║
    ║                                                          ║
    ║  [✓] Runtime    : 8 步 Claude Code harness loop          ║
    ║  [✓] Context    : append-only event log + filesystem mem  ║
    ║  [✓] Capability : 29 lark-cli SKILL + 3-Agent workforce  ║
    ║  [✓] Governance : 4 级权限 + owner_lock + audit          ║
    ║  [✓] Surface    : IM + Dashboard + Flutter + MCP/ACP     ║
    ╚══════════════════════════════════════════════════════════╝
"""


def _validate_config() -> None:
    if not os.getenv("FEISHU_APP_ID") or os.getenv("FEISHU_APP_ID") == "cli_your_app_id_here":
        logger.warning("FEISHU_APP_ID 未配置 — bot 模式将无法启动；dashboard 仍可运行")


def cmd_bot() -> None:
    """启动飞书机器人长连接."""
    from pilot.surface.feishu.bot import run as run_bot

    _validate_config()
    logger.info("启动飞书机器人...")
    run_bot()


def cmd_dashboard() -> None:
    """启动 Web Dashboard."""
    from pilot.surface.dashboard.server import run as run_dashboard

    port = int(os.getenv("DASHBOARD_PORT", "8001"))
    logger.info("启动 Dashboard on :%d", port)
    run_dashboard(host="0.0.0.0", port=port)


def cmd_mcp() -> None:
    """启动 MCP server（反向暴露给 Cursor / Claude）."""
    from pilot.surface.mcp_server import run as run_mcp

    port = int(os.getenv("MCP_SERVER_PORT", "8003"))
    logger.info("启动 MCP server on :%d", port)
    run_mcp(host="0.0.0.0", port=port)


def cmd_all() -> None:
    """同时启动 bot + dashboard + sync hub + mcp，并发跑."""
    import threading

    _validate_config()

    threads = []
    try:
        from pilot.surface.feishu.bot import run as run_bot
        threads.append(threading.Thread(target=run_bot, name="bot", daemon=True))
    except Exception as e:
        logger.warning("bot 模块未就绪: %s", e)

    try:
        from pilot.surface.dashboard.server import run as run_dashboard

        port = int(os.getenv("DASHBOARD_PORT", "8001"))
        threads.append(threading.Thread(
            target=lambda: run_dashboard(host="0.0.0.0", port=port),
            name="dashboard",
            daemon=True,
        ))
    except Exception as e:
        logger.warning("dashboard 模块未就绪: %s", e)

    if not threads:
        logger.error("没有可启动的服务，请检查依赖")
        sys.exit(1)

    for t in threads:
        t.start()
        logger.info("线程已启动: %s", t.name)

    def _shutdown(signum, _frame):
        logger.info("收到信号 %s，正在退出...", signal.Signals(signum).name)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for t in threads:
        t.join()


def main() -> None:
    print(BANNER)
    parser = argparse.ArgumentParser(prog="agent-pilot", description="Agent-Pilot V1")
    parser.add_argument(
        "command",
        choices=["bot", "dashboard", "mcp", "all"],
        nargs="?",
        default="all",
        help="子命令（默认 all）",
    )
    args = parser.parse_args()

    cmd_map = {
        "bot": cmd_bot,
        "dashboard": cmd_dashboard,
        "mcp": cmd_mcp,
        "all": cmd_all,
    }
    cmd_map[args.command]()


if __name__ == "__main__":
    main()
