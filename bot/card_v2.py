"""Feishu Card Schema 2.0 builder primitives.

Shared by cards_pilot.py and other card modules for constructing
interactive message cards that conform to Feishu's Schema 2.0 format.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _header(
    title: str,
    *,
    subtitle: str = "",
    template: str = "blue",
) -> Dict[str, Any]:
    h: Dict[str, Any] = {
        "title": {"tag": "plain_text", "content": title},
        "template": template,
    }
    if subtitle:
        h["subtitle"] = {"tag": "plain_text", "content": subtitle}
    return h


def _text(content: str, eid: str = "") -> Dict[str, Any]:
    el: Dict[str, Any] = {
        "tag": "div",
        "text": {"tag": "lark_md", "content": content},
    }
    if eid:
        el["element_id"] = eid
    return el


def _divider() -> Dict[str, Any]:
    return {"tag": "hr"}


def _button(
    label: str,
    *,
    action: str = "",
    value: Optional[Dict[str, Any]] = None,
    url: str = "",
    style: str = "default",
    eid: str = "",
) -> Dict[str, Any]:
    btn: Dict[str, Any] = {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": style,
    }
    if value is not None:
        btn["value"] = {**(value or {}), "action": action} if action else value
    elif action:
        btn["value"] = {"action": action}
    if url:
        btn["url"] = url
    if eid:
        btn["element_id"] = eid
    return btn


def _column(element: Dict[str, Any], weight: int = 1) -> Dict[str, Any]:
    return {
        "tag": "column",
        "width": f"weighted",
        "weight": weight,
        "elements": [element],
    }


def _columns(*cols: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tag": "column_set",
        "columns": list(cols),
        "flex_mode": "bisect",
    }


def _collapsible(
    title: str,
    content: Dict[str, Any],
    *,
    expanded: bool = False,
    eid: str = "",
) -> Dict[str, Any]:
    el: Dict[str, Any] = {
        "tag": "collapsible_panel",
        "header": {"tag": "plain_text", "content": title},
        "elements": [content],
        "expanded": expanded,
    }
    if eid:
        el["element_id"] = eid
    return el


def _envelope(
    header: Dict[str, Any],
    body: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "type": "template",
        "data": {
            "template_id": "",
            "template_variable": {},
        },
        "header": header,
        "elements": body,
    }
