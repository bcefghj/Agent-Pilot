"""MCP Server — 把 V1 的 Capability 工具反向暴露给 Cursor / Claude / Trae.

V1 的工具 → MCP tools；外部 AI client 配置后即可调用：
  - doc.create / doc.append
  - canvas.create
  - slide.generate
  - archive.bundle
  ...

Note: 真完整 MCP server 需要 mcp 包；本实现用最简 HTTP /JSON-RPC 模拟，
保证零 mcp 依赖也可启动；mcp 包可装后无缝升级。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("pilot.surface.mcp_server")


def create_app():
    """构建 FastAPI app 当 MCP server 用（HTTP/JSON-RPC 子集）."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Agent-Pilot V1 · MCP Server", version="1.0.0")

    # ── tools/list ──
    @app.post("/tools/list")
    @app.get("/tools/list")
    async def tools_list():
        from pilot.capability.tools.registry import default_registry

        reg = default_registry()
        return {"tools": [
            {
                "name": s.name,
                "description": s.description,
                "inputSchema": s.input_schema,
            }
            for s in reg.list_specs()
        ]}

    # ── tools/call ──
    @app.post("/tools/call")
    async def tools_call(req: Request):
        body = await req.json()
        name = body.get("name", "")
        args = body.get("arguments", {})
        try:
            from pilot.capability.tools.registry import default_registry

            reg = default_registry()
            result = await reg.execute(tool_name=name, tool_input=args, ctx={"_via_mcp": True})
            return {"content": [{"type": "json", "json": result}], "isError": False}
        except Exception as e:
            logger.exception("MCP tool call %s failed: %s", name, e)
            return JSONResponse(
                {"content": [{"type": "text", "text": str(e)}], "isError": True},
                status_code=200,
            )

    # ── resources/list（暴露 sessions 与 artifacts 作为可读资源）──
    @app.get("/resources/list")
    async def resources_list():
        from pilot.runtime.checkpoint import list_sessions

        sessions = list_sessions(limit=50)
        return {"resources": [
            {
                "uri": f"pilot://session/{s['session_id']}",
                "name": f"Session {s['session_id'][:16]}",
                "mimeType": "application/json",
                "description": f"mode={s.get('mode')} updated_at={s.get('updated_at')}",
            }
            for s in sessions
        ]}

    @app.get("/")
    async def index():
        return {
            "name": "Agent-Pilot V1 MCP Server",
            "version": "1.0.0",
            "protocol": "MCP (HTTP/JSON-RPC subset)",
            "endpoints": ["/tools/list", "/tools/call", "/resources/list"],
            "note": "Configure your AI client (Cursor/Claude/Trae) with this URL to enable reverse-call.",
        }

    return app


def run(*, host: str = "0.0.0.0", port: int = 8003) -> None:
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="warning")
