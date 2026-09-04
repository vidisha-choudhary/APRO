"""Tests for deterministic event ordering and causal validation."""

from datetime import UTC, datetime, timedelta

from apro.audit.enums import AuditEventType
from apro.audit.integrity import AuditIntegrityChecker
from apro.domain.enums import AuditActor
from apro.domain.models import AuditEvent


def test_deterministic_sorting() -> None:
    """Audit events sort deterministically by timestamp then audit_event_id."""
    base_time = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    ev1 = AuditEvent(
        audit_event_id="aud_b",
        case_id="c1",
        event_type=AuditEventType.CASE_CREATED,
        actor=AuditActor.SYSTEM,
        timestamp=base_time,
        payload={"seq": 1},
    )
    ev2 = AuditEvent(
        audit_event_id="aud_a",
        case_id="c1",
        event_type=AuditEventType.DIAGNOSIS_CREATED,
        actor=AuditActor.MODEL,
        timestamp=base_time,
        payload={"seq": 2},
    )
    ev3 = AuditEvent(
        audit_event_id="aud_c",
        case_id="c1",
        event_type=AuditEventType.EXECUTION_STARTED,
        actor=AuditActor.EXECUTOR,
        timestamp=base_time + timedelta(seconds=1),
        payload={"seq": 3},
    )

    unordered = [ev3, ev1, ev2]
    ordered = sorted(unordered, key=lambda e: (e.timestamp, e.audit_event_id))

    assert ordered == [ev2, ev1, ev3]


def test_causal_ordering_integrity_check() -> None:
    """Integrity checker detects out-of-order execution completion without start."""
    now = datetime.now(UTC)
    bad_events = [
        AuditEvent(
            audit_event_id="aud_1",
            case_id="c1",
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
        ),
        AuditEvent(
            audit_event_id="aud_2",
            case_id="c1",
            event_type=AuditEventType.EXECUTION_COMPLETED,
            actor=AuditActor.EXECUTOR,
            timestamp=now + timedelta(seconds=1),
        ),
    ]
    is_valid, issues = AuditIntegrityChecker.validate_events_integrity("c1", bad_events)
    assert not is_valid
    assert any("occurred before EXECUTION_STARTED" in issue for issue in issues)
