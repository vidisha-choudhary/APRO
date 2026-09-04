"""Async task-local correlation context propagation for Phase 14."""

import uuid
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

_current_case_id: ContextVar[str | None] = ContextVar(
    "apro_audit_case_id", default=None
)
_current_trace_id: ContextVar[str | None] = ContextVar(
    "apro_audit_trace_id", default=None
)
_current_cycle_id: ContextVar[int | str | None] = ContextVar(
    "apro_audit_cycle_id", default=None
)


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable representation of the active correlation context."""

    case_id: str | None = None
    trace_id: str | None = None
    cycle_id: int | str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert non-null correlation IDs to a dictionary."""
        result: dict[str, Any] = {}
        if self.case_id is not None:
            result["case_id"] = self.case_id
        if self.trace_id is not None:
            result["trace_id"] = self.trace_id
        if self.cycle_id is not None:
            result["cycle_id"] = self.cycle_id
        return result


def generate_trace_id() -> str:
    """Generate a unique trace identifier."""
    return f"trace_{uuid.uuid4().hex}"


def get_correlation_context() -> CorrelationContext:
    """Retrieve the current task-local correlation context."""
    return CorrelationContext(
        case_id=_current_case_id.get(),
        trace_id=_current_trace_id.get(),
        cycle_id=_current_cycle_id.get(),
    )


def set_correlation_context(
    case_id: str | None = None,
    trace_id: str | None = None,
    cycle_id: int | str | None = None,
) -> tuple[Token[str | None], Token[str | None], Token[int | str | None]]:
    """Set active correlation context and return reset tokens."""
    token_case = _current_case_id.set(case_id)
    token_trace = _current_trace_id.set(trace_id or generate_trace_id())
    token_cycle = _current_cycle_id.set(cycle_id)
    return token_case, token_trace, token_cycle


def reset_correlation_context(
    tokens: tuple[Token[str | None], Token[str | None], Token[int | str | None]],
) -> None:
    """Reset correlation context using previous tokens."""
    token_case, token_trace, token_cycle = tokens
    _current_case_id.reset(token_case)
    _current_trace_id.reset(token_trace)
    _current_cycle_id.reset(token_cycle)


def clear_correlation_context() -> None:
    """Clear all correlation context values for current task."""
    _current_case_id.set(None)
    _current_trace_id.set(None)
    _current_cycle_id.set(None)


@contextmanager
def correlation_scope(
    case_id: str | None = None,
    trace_id: str | None = None,
    cycle_id: int | str | None = None,
) -> Generator[CorrelationContext, None, None]:
    """Synchronous context manager for correlation context."""
    tokens = set_correlation_context(case_id, trace_id, cycle_id)
    try:
        yield get_correlation_context()
    finally:
        reset_correlation_context(tokens)


@asynccontextmanager
async def async_correlation_scope(
    case_id: str | None = None,
    trace_id: str | None = None,
    cycle_id: int | str | None = None,
) -> AsyncGenerator[CorrelationContext, None]:
    """Asynchronous context manager for correlation context."""
    tokens = set_correlation_context(case_id, trace_id, cycle_id)
    try:
        yield get_correlation_context()
    finally:
        reset_correlation_context(tokens)
