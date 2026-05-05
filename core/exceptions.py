"""Unified exception hierarchy for Agent-Pilot.

Every exception carries structured fields for logging (structlog-friendly)
and a user-facing Chinese message suitable for Feishu card responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class AgentPilotError(Exception):
    """所有 Agent-Pilot 异常的根基类。"""

    error_code: str = "AGENT_PILOT_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_user_message(self) -> str:
        """返回面向终端用户的中文提示（可直接放入飞书消息卡片）。"""
        return f"系统遇到问题，请稍后重试。如持续出现请联系管理员。（错误码：{self.error_code}）"

    def to_log_dict(self) -> dict[str, Any]:
        """返回适合 structlog 绑定的字典。"""
        return {
            "error_type": type(self).__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r}, details={self.details!r})"


# ─── Configuration ────────────────────────────────────────────────────────────


class ConfigError(AgentPilotError):
    """配置项缺失或格式不合法。"""

    error_code = "CONFIG_ERROR"

    def __init__(self, message: str, *, field: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details={**(details or {}), "field": field})
        self.field = field

    def to_user_message(self) -> str:
        hint = f"（配置项：{self.field}）" if self.field else ""
        return f"系统配置异常{hint}，请联系管理员检查部署配置。"


# ─── Feishu API ───────────────────────────────────────────────────────────────


class FeishuAPIError(AgentPilotError):
    """飞书开放平台 API 调用失败。"""

    error_code = "FEISHU_API_ERROR"

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        request_id: str = "",
        api_path: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={
                **(details or {}),
                "status_code": status_code,
                "request_id": request_id,
                "api_path": api_path,
            },
        )
        self.status_code = status_code
        self.request_id = request_id
        self.api_path = api_path

    def to_user_message(self) -> str:
        if 400 <= self.status_code < 500:
            return "飞书接口权限不足或请求参数有误，请检查应用授权配置。"
        if self.status_code >= 500:
            return "飞书服务暂时不可用，请稍后重试。"
        return "与飞书通信时出现问题，请稍后重试。"

    def to_log_dict(self) -> dict[str, Any]:
        d = super().to_log_dict()
        d.update(status_code=self.status_code, request_id=self.request_id, api_path=self.api_path)
        return d


# ─── LLM Provider ─────────────────────────────────────────────────────────────


class LLMError(AgentPilotError):
    """LLM 提供商调用失败（火山方舟 / DeepSeek / MiniMax 等）。"""

    error_code = "LLM_ERROR"

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        model: str = "",
        retries_attempted: int = 0,
        is_retryable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={
                **(details or {}),
                "provider": provider,
                "model": model,
                "retries_attempted": retries_attempted,
                "is_retryable": is_retryable,
            },
        )
        self.provider = provider
        self.model = model
        self.retries_attempted = retries_attempted
        self.is_retryable = is_retryable

    def to_user_message(self) -> str:
        if self.is_retryable:
            return f"AI 模型（{self.provider}）响应超时，系统将自动重试。"
        return f"AI 模型（{self.provider}）暂时不可用，请稍后再试或切换模型。"

    def to_log_dict(self) -> dict[str, Any]:
        d = super().to_log_dict()
        d.update(provider=self.provider, model=self.model, retries_attempted=self.retries_attempted)
        return d


# ─── Tool Execution ───────────────────────────────────────────────────────────


class ToolExecutionError(AgentPilotError):
    """Agent 工具链中某步执行失败。"""

    error_code = "TOOL_EXECUTION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        tool_name: str = "",
        step_id: str = "",
        input_summary: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={
                **(details or {}),
                "tool_name": tool_name,
                "step_id": step_id,
                "input_summary": input_summary,
            },
        )
        self.tool_name = tool_name
        self.step_id = step_id
        self.input_summary = input_summary

    def to_user_message(self) -> str:
        name = self.tool_name or "未知工具"
        return f"执行工具「{name}」时出错，系统正在尝试恢复。"

    def to_log_dict(self) -> dict[str, Any]:
        d = super().to_log_dict()
        d.update(tool_name=self.tool_name, step_id=self.step_id)
        return d


# ─── Permission ───────────────────────────────────────────────────────────────


class PermissionDeniedError(AgentPilotError):
    """权限校验未通过（飞书权限 / 内部 RBAC）。"""

    error_code = "PERMISSION_DENIED"

    def __init__(
        self,
        message: str,
        *,
        user_id: str = "",
        required_scope: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={**(details or {}), "user_id": user_id, "required_scope": required_scope},
        )
        self.user_id = user_id
        self.required_scope = required_scope

    def to_user_message(self) -> str:
        return "您没有执行该操作的权限。如有疑问请联系管理员。"


# ─── Planning / Orchestration ─────────────────────────────────────────────────


class PlanningError(AgentPilotError):
    """Planner / Orchestrator 阶段失败（意图解析、计划编排等）。"""

    error_code = "PLANNING_ERROR"

    def __init__(
        self,
        message: str,
        *,
        phase: str = "",
        plan_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={**(details or {}), "phase": phase, "plan_id": plan_id},
        )
        self.phase = phase
        self.plan_id = plan_id

    def to_user_message(self) -> str:
        return "系统在理解您的意图时遇到困难，请尝试简化描述后重试。"


# ─── Multi-device Sync ────────────────────────────────────────────────────────


class SyncError(AgentPilotError):
    """多端同步失败（WebSocket / CRDT 合并冲突等）。"""

    error_code = "SYNC_ERROR"

    def __init__(
        self,
        message: str,
        *,
        device_id: str = "",
        conflict_type: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={**(details or {}), "device_id": device_id, "conflict_type": conflict_type},
        )
        self.device_id = device_id
        self.conflict_type = conflict_type

    def to_user_message(self) -> str:
        return "多端同步出现冲突，系统已自动保留最新版本。如数据有误请手动刷新。"


# ─── Rate Limiting ────────────────────────────────────────────────────────────


class RateLimitError(AgentPilotError):
    """请求频率超限（飞书 API / LLM provider 限流）。"""

    error_code = "RATE_LIMIT_ERROR"

    def __init__(
        self,
        message: str,
        *,
        retry_after: float = 0.0,
        limit_type: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            details={**(details or {}), "retry_after": retry_after, "limit_type": limit_type},
        )
        self.retry_after = retry_after
        self.limit_type = limit_type

    def to_user_message(self) -> str:
        if self.retry_after > 0:
            return f"请求过于频繁，请在 {self.retry_after:.0f} 秒后重试。"
        return "请求过于频繁，请稍后重试。"

    def to_log_dict(self) -> dict[str, Any]:
        d = super().to_log_dict()
        d.update(retry_after=self.retry_after, limit_type=self.limit_type)
        return d
