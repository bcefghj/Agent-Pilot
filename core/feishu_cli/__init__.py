"""Feishu CLI integration layer.

Provides MCP server configuration for lark-openapi-mcp and helpers to
check availability and enumerate supported skills at runtime.
Supports 24 Feishu CLI Skills across 17+ business domains.
"""

from .mcp_config import (
    FEISHU_CLI_SKILLS,
    MCP_SERVER_CONFIG,
    get_all_commands,
    get_mcp_tools,
    get_skill_by_name,
    is_cli_available,
    is_mcp_available,
    list_skill_names,
    run_cli_command,
)

__all__ = [
    "MCP_SERVER_CONFIG",
    "FEISHU_CLI_SKILLS",
    "is_mcp_available",
    "is_cli_available",
    "get_mcp_tools",
    "get_skill_by_name",
    "list_skill_names",
    "get_all_commands",
    "run_cli_command",
]
