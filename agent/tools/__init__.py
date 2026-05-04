"""Unified Tool Registry · 把 Shield v3 / Mentor v4 / Feishu API 所有能力塌缩为 @tool。"""

# Import tool modules so decorators register themselves
from . import (
    archive_tools,  # noqa: F401
    canvas_tools,  # noqa: F401
    doc_tools,  # noqa: F401
    im_tools,  # noqa: F401
    lark_cli_tools,  # noqa: F401
    memory_tools,  # noqa: F401
    mentor_tools,  # noqa: F401
    slides_tools,  # noqa: F401
)
from .registry import get_registry, register_builtin_tools, tool

register_builtin_tools()

__all__ = ["tool", "get_registry"]
