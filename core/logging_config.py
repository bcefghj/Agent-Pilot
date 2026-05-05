"""Structlog configuration for Agent-Pilot.

Usage::

    from core.logging_config import setup_logging, get_logger

    setup_logging()                   # call once at startup
    log = get_logger("my_module")     # per-module logger
    log.info("event_name", user_id="u123", plan_id="p456")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def setup_logging(
    *,
    level: str = "INFO",
    log_format: str = "console",
    default_context: dict[str, Any] | None = None,
) -> None:
    """Initialize structlog + stdlib logging.

    Args:
        level: Root log level (DEBUG / INFO / WARNING / ERROR).
        log_format: ``"json"`` for production, ``"console"`` for colored dev output.
        default_context: Extra key-value pairs bound to every log line
                         (e.g. ``{"service": "agent-pilot"}``).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(log_level)

    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "websockets"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if default_context:
        structlog.contextvars.bind_contextvars(**default_context)


def get_logger(name: str, **initial_bind: Any) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to *name* and optional initial context."""
    log: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if initial_bind:
        log = log.bind(**initial_bind)
    return log


def bind_context(**kwargs: Any) -> None:
    """Bind context variables that persist across all loggers in the current context.

    Typical usage in a request handler::

        bind_context(request_id=req_id, user_id=user_id)
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables (call at the end of a request cycle)."""
    structlog.contextvars.clear_contextvars()
