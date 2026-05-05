"""Agent-Pilot MCP Server.

Exposes Agent-Pilot capabilities over the Model Context Protocol so any
MCP-compatible client (Cursor, Claude Code, custom agents) can invoke
task creation, document generation, slide creation, and more.

Run as a stand-alone process::

    python -m core.mcp_server.server                    # stdio transport
    python -m core.mcp_server.server --transport sse    # SSE for Cursor
    python -m core.mcp_server.server --transport http   # plain HTTP fallback

The protocol layer is intentionally optional – if the ``mcp`` package is
not installed, a lightweight HTTP JSON server is used instead.
"""

from .tools import TOOL_REGISTRY, TOOL_SCHEMAS  # noqa: F401
