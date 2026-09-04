"""Tests verifying complete absence of sentinel secrets in telemetry."""

from datetime import UTC, datetime

import pytest

from apro.audit.logging import LogCaptureHandler, get_structured_logger
from apro.audit.reconstruction import CaseReconstructionService
from apro.audit.service import AuditService
from apro.domain.enums import (
    FailureCategory,
    RecoveryCaseStatus,
)
from apro.domain.models import (
    Diagnosis,
    RecoveryCase,
)


@pytest.mark.asyncio
async def test_sentinel_secret_leakage_prevention() -> None:
    """Sentinel secret is absent from logs, audit events, and reconstruction output."""
    sentinel = "sentinel_phase14_secret_87654321"
    now = datetime.now(UTC)
    case_id = "case_secret_test"

    # 1. Logging verification
    logger = get_structured_logger("secret.test.logger")
    capture = LogCaptureHandler()
    logger.logger.addHandler(capture)

    logger.info(
        "TEST_SECRET_EVENT",
        metadata={
            "api_key": sentinel,
            "Authorization": f"Bearer {sentinel}",
            "error_msg": f"Failed with {sentinel}",
        },
    )
    assert len(capture.raw_records) >= 1
    log_dump = str(capture.raw_records[-1])
    assert sentinel not in log_dump
    logger.logger.removeHandler(capture)

    # 2. Audit Event payload verification
    service = AuditService()
    ev = await service.record_event(
        case_id=case_id,
        event_type="SECRET_TEST_EVENT",
        payload={
            "password": sentinel,
            "card_number": "4111222233334444",
            "nested": {"secret": sentinel},
        },
    )
    event_str = str(ev.model_dump())
    assert sentinel not in event_str

    # 3. Reconstruction verification
    case = RecoveryCase(
        case_id=case_id,
        payment_id="pay_sec",
        customer_id="cust_sec",
        status=RecoveryCaseStatus.RECOVERED,
        opened_at=now,
        updated_at=now,
    )
    diag = Diagnosis(
        diagnosis_id="diag_sec",
        case_id=case_id,
        category=FailureCategory.CUSTOMER_SIDE,
        confidence=0.9,
        evidence=(f"Evidence with {sentinel}",),
        model_name="diag_v1",
        model_version="1.0.0",
        created_at=now,
    )
    trace = await CaseReconstructionService.reconstruct_case(
        case_id=case_id,
        case=case,
        diagnosis=diag,
        audit_events=[ev],
    )
    trace_dump = str(trace.model_dump())
    assert sentinel not in trace_dump
