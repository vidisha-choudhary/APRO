"""Tests for StructuredLogger, JSON formatting, and fail-safe telemetry."""

from apro.audit.correlation import correlation_scope
from apro.audit.logging import (
    LogCaptureHandler,
    get_structured_logger,
    get_telemetry_failure_count,
    reset_telemetry_failure_count,
)


def test_structured_logger_json_output() -> None:
    """StructuredLogger produces formatted JSON records."""
    logger = get_structured_logger("test.logger")
    capture = LogCaptureHandler()
    logger.logger.addHandler(capture)

    with correlation_scope(
        case_id="case_log_test", trace_id="trace_log_test", cycle_id=1
    ):
        logger.info(
            "DECISION_CREATED",
            status="SUCCESS",
            reason_code="RC_OK",
            duration_ms=45.2,
            metadata={"candidate_count": 3},
        )

    assert len(capture.entries) >= 1
    last_entry = capture.entries[-1]
    assert last_entry.event_name == "DECISION_CREATED"
    assert last_entry.case_id == "case_log_test"
    assert last_entry.trace_id == "trace_log_test"
    assert last_entry.cycle_id == 1
    assert last_entry.status == "SUCCESS"
    assert last_entry.duration_ms == 45.2

    logger.logger.removeHandler(capture)


def test_telemetry_failure_counter() -> None:
    """Telemetry sink failure counter tracks handler errors safely."""
    reset_telemetry_failure_count()
    assert get_telemetry_failure_count() == 0
