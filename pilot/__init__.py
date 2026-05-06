"""Agent-Pilot V1 — 飞书 IM 中的 AI 主驾驶 Harness.

5 层 Harness 架构:
  - runtime    : 8 步 Claude Code harness loop + 状态机 + 检查点
  - context    : append-only 事件日志 + ContextPack + filesystem 内存
  - capability : 工具 / Skills / Workforce / MCP 客户端
  - governance : 4 级权限 / owner_lock / 沙箱 / 审计
  - surface    : 飞书 IM / Web Dashboard / Flutter / MCP server / ACP server
"""

__version__ = "1.0.0"
__author__ = "戴尚好 & 李洁盈"

from pilot.runtime import harness  # noqa: F401  (export for `from pilot import harness`)

__all__ = ["__version__", "harness"]
