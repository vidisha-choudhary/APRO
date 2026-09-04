"""Structured JSON logger with automated correlation for Phase 14."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from apro.audit.correlation import get_correlation_context
from apro.audit.enums import AuditLogLevel
from apro.audit.models import StructuredLogEntry
from apro.audit.sanitization import TelemetrySanitizer

_telemetry_failure_count: int = 0


def get_telemetry_failure_count() -> int:
    """Return the total number of telemetry sink errors encountered."""
    return _telemetry_failure_count


def reset_telemetry_failure_count() -> None:
    """Reset telemetry sink failure counter."""
    global _telemetry_failure_count
    _telemetry_failure_count = 0


class LogCaptureHandler(logging.Handler):
    """In-memory logging handler for capturing structured JSON logs in tests."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(StructuredJSONFormatter())
        self.entries: list[StructuredLogEntry] = []
        self.raw_records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            parsed = json.loads(msg)
            self.raw_records.append(parsed)
            entry = StructuredLogEntry(
                timestamp=datetime.fromisoformat(parsed["timestamp"]),
                level=parsed["level"],
                service=parsed.get("service", "apro"),
                event_name=parsed["event_name"],
                case_id=parsed.get("case_id"),
                trace_id=parsed.get("trace_id"),
                cycle_id=parsed.get("cycle_id"),
                entity_id=parsed.get("entity_id"),
                phase=parsed.get("phase"),
                status=parsed.get("status"),
                reason_code=parsed.get("reason_code"),
                duration_ms=parsed.get("duration_ms"),
                exception_type=parsed.get("exception_type"),
                version=parsed.get("version"),
                metadata=parsed.get("metadata", {}),
            )
            self.entries.append(entry)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            global _telemetry_failure_count
            _telemetry_failure_count += 1
            sys.stderr.write(f"LogCaptureHandler parse error: {exc}\n")

    def clear(self) -> None:
        """Clear all captured logs."""
        self.entries.clear()
        self.raw_records.clear()


class StructuredJSONFormatter(logging.Formatter):
    """Formatter that produces sanitized structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        # Pull extra attributes attached to record
        payload = getattr(record, "structured_payload", None)
        if payload is None:
            # Fallback formatting for regular logging calls
            corr = get_correlation_context()
            payload = {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "service": "apro",
                "event_name": record.getMessage(),
                "case_id": corr.case_id,
                "trace_id": corr.trace_id,
                "cycle_id": corr.cycle_id,
                "metadata": {},
            }
        # Sanitize before JSON serialization
        sanitized = TelemetrySanitizer.sanitize(payload)
        return json.dumps(sanitized, default=str)


class StructuredLogger:
    """Safe structured logger for operational events with automated correlation."""

    def __init__(self, name: str = "apro.audit") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

    def log_event(
        self,
        event_name: str,
        level: AuditLogLevel = AuditLogLevel.INFO,
        case_id: str | None = None,
        trace_id: str | None = None,
        cycle_id: int | str | None = None,
        entity_id: str | None = None,
        phase: str | None = None,
        status: str | None = None,
        reason_code: str | None = None,
        duration_ms: float | None = None,
        exception: BaseException | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a structured operational event."""
        corr = get_correlation_context()
        resolved_case_id = case_id or corr.case_id
        resolved_trace_id = trace_id or corr.trace_id
        resolved_cycle_id = cycle_id or corr.cycle_id

        exc_type = exception.__class__.__name__ if exception else None
        meta = metadata or {}
        if exception:
            meta["exception_details"] = TelemetrySanitizer.sanitize_exception(exception)

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": str(level),
            "service": "apro",
            "event_name": event_name,
            "case_id": resolved_case_id,
            "trace_id": resolved_trace_id,
            "cycle_id": resolved_cycle_id,
            "entity_id": entity_id,
            "phase": phase,
            "status": status,
            "reason_code": reason_code,
            "duration_ms": duration_ms,
            "exception_type": exc_type,
            "version": version,
            "metadata": meta,
        }

        # Format record
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=getattr(logging, str(level).upper(), logging.INFO),
            fn="",
            lno=0,
            msg=event_name,
            args=(),
            exc_info=None,
        )
        record.structured_payload = payload

        try:
            self.logger.handle(record)
        except (OSError, UnicodeEncodeError) as exc:
            global _telemetry_failure_count
            _telemetry_failure_count += 1
            sys.stderr.write(f"Telemetry sink I/O failure: {exc}\n")

    def debug(self, event_name: str, **kwargs: Any) -> None:
        self.log_event(event_name, level=AuditLogLevel.DEBUG, **kwargs)

    def info(self, event_name: str, **kwargs: Any) -> None:
        self.log_event(event_name, level=AuditLogLevel.INFO, **kwargs)

    def warning(self, event_name: str, **kwargs: Any) -> None:
        self.log_event(event_name, level=AuditLogLevel.WARNING, **kwargs)

    def error(self, event_name: str, **kwargs: Any) -> None:
        self.log_event(event_name, level=AuditLogLevel.ERROR, **kwargs)

    def critical(self, event_name: str, **kwargs: Any) -> None:
        self.log_event(event_name, level=AuditLogLevel.CRITICAL, **kwargs)


def get_structured_logger(name: str = "apro.audit") -> StructuredLogger:
    """Factory for obtaining a StructuredLogger instance."""
    return StructuredLogger(name)
