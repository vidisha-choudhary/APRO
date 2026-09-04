"""Tests for audit domain models, schema constraints, and frozen immutability."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from apro.audit.enums import AUDIT_SCHEMA_VERSION, AuditCompleteness, AuditEventType
from apro.audit.models import (
    CaseAuditTrace,
    StructuredLogEntry,
)
from apro.domain.enums import AuditActor
from apro.domain.models import AuditEvent


def test_audit_event_immutability() -> None:
    """AuditEvent is frozen and rejects attribute mutation."""
    event = AuditEvent(
        audit_event_id="aud_123",
        case_id="case_123",
        event_type=AuditEventType.CASE_CREATED,
        actor=AuditActor.SYSTEM,
        timestamp=datetime.now(UTC),
        payload={"key": "val"},
        correlation_id="corr_123",
    )

    with pytest.raises(ValidationError, match="Instance is frozen"):
        event.event_type = "CHANGED"  # type: ignore[misc]


def test_structured_log_entry_fields() -> None:
    """StructuredLogEntry produces valid frozen JSON log records."""
    now = datetime.now(UTC)
    entry = StructuredLogEntry(
        timestamp=now,
        level="INFO",
        service="apro",
        event_name="POLICY_DECISION_CREATED",
        case_id="c_1",
        trace_id="t_1",
        cycle_id=1,
        entity_id="pol_1",
        phase="policy",
        status="ALLOW",
        reason_code="RC_ALLOW",
        duration_ms=12.5,
        version="1.0.0",
        metadata={"custom": 123},
    )
    assert entry.level == "INFO"
    assert entry.case_id == "c_1"
    assert entry.duration_ms == 12.5

    with pytest.raises(ValidationError, match="Instance is frozen"):
        entry.level = "ERROR"  # type: ignore[misc]


def test_case_audit_trace_defaults() -> None:
    """CaseAuditTrace correctly initializes with default schema versions."""
    trace = CaseAuditTrace(
        case_id="case_abc",
        trace_id="trace_abc",
        final_case_status="RECOVERED",
        total_amount_recovered=5000,
        completeness=AuditCompleteness.COMPLETE,
        integrity_valid=True,
    )
    assert trace.schema_version == AUDIT_SCHEMA_VERSION
    assert trace.cycles == []
    assert trace.events == []
    assert trace.final_case_status == "RECOVERED"
