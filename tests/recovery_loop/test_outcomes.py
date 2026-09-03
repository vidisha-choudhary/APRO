"""Unit tests for Phase 13 OutcomeProcessor and evidence classification."""

from datetime import UTC, datetime

import pytest

from apro.domain.enums import (
    ExecutionMode,
    ExecutionStatus,
    OutcomeType,
    PaymentStatus,
    RecoveryCaseStatus,
)
from apro.domain.models import Execution, Payment, RecoveryCase
from apro.recovery_loop.enums import EvidenceType, RecoveryLoopDisposition
from apro.recovery_loop.exceptions import (
    EntityMismatchError,
    TerminalCaseReopenError,
)
from apro.recovery_loop.models import OutcomeEvidence
from apro.recovery_loop.outcomes import OutcomeProcessor


def _sample_payment(status: PaymentStatus = PaymentStatus.FAILED) -> Payment:
    now = datetime.now(UTC)
    return Payment(
        payment_id="pay_001",
        customer_id="cust_001",
        provider="razorpay",
        amount=50000,
        currency="INR",
        method="card",
        status=status,
        created_at=now,
        updated_at=now,
    )


def _sample_case(
    status: RecoveryCaseStatus = RecoveryCaseStatus.OBSERVING,
) -> RecoveryCase:
    now = datetime.now(UTC)
    return RecoveryCase(
        case_id="case_001",
        payment_id="pay_001",
        customer_id="cust_001",
        status=status,
        opened_at=now,
        updated_at=now,
        recovery_amount=50000,
        current_attempt_count=1,
    )


@pytest.mark.asyncio
async def test_execution_succeeded_without_capture_maps_to_pending() -> None:
    """Invariant: Execution != Recovery. ExecutionStatus.SUCCEEDED without
    capture proof is PENDING.
    """
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    execution = Execution(
        execution_id="exec_001",
        action_id="act_001",
        case_id="case_001",
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
    )

    evidence = OutcomeEvidence(
        evidence_id="ev_001",
        case_id="case_001",
        execution_id="exec_001",
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    res, updated_case, updated_payment = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
        execution=execution,
    )

    assert res.outcome.type == OutcomeType.PENDING
    assert res.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME
    assert updated_case.status == RecoveryCaseStatus.OBSERVING
    assert updated_payment.status == PaymentStatus.FAILED


@pytest.mark.asyncio
async def test_execution_unknown_maps_to_pending_not_false_failed() -> None:
    """Invariant: ExecutionStatus.UNKNOWN is indeterminate, not false FAILED."""
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    execution = Execution(
        execution_id="exec_002",
        action_id="act_002",
        case_id="case_001",
        execution_type="RETRY",
        execution_mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.UNKNOWN,
        started_at=now,
        completed_at=now,
    )

    evidence = OutcomeEvidence(
        evidence_id="ev_002",
        case_id="case_001",
        execution_id="exec_002",
        evidence_type=EvidenceType.EXECUTION_RESULT,
        observed_at=now,
    )

    res, updated_case, _ = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
        execution=execution,
    )

    assert res.outcome.type == OutcomeType.PENDING
    assert res.disposition == RecoveryLoopDisposition.WAIT_FOR_OUTCOME


@pytest.mark.asyncio
async def test_recovery_confirmed_advances_case_to_recovered() -> None:
    """Recovery evidence advances case and payment to RECOVERED / CAPTURED."""
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    evidence = OutcomeEvidence(
        evidence_id="ev_003",
        case_id="case_001",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.CAPTURED,
        amount_recovered=50000,
        observed_at=now,
    )

    res, updated_case, updated_payment = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
    )

    assert res.outcome.type == OutcomeType.RECOVERED
    assert res.disposition == RecoveryLoopDisposition.COMPLETE
    assert updated_case.status == RecoveryCaseStatus.RECOVERED
    assert updated_payment.status == PaymentStatus.CAPTURED
    assert updated_case.closed_at is not None


@pytest.mark.asyncio
async def test_failed_outcome_advances_case_to_evaluating() -> None:
    """Definitive failed recovery outcome advances case to EVALUATING for
    re-evaluation.
    """
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    evidence = OutcomeEvidence(
        evidence_id="ev_004",
        case_id="case_001",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.FAILED,
        observed_at=now,
    )

    res, updated_case, _ = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
    )

    assert res.outcome.type == OutcomeType.FAILED
    assert res.disposition == RecoveryLoopDisposition.RE_EVALUATE
    assert updated_case.status == RecoveryCaseStatus.EVALUATING


@pytest.mark.asyncio
async def test_entity_mismatch_raises_error() -> None:
    """Mismatched case_id or payment_id raises EntityMismatchError."""
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    mismatched_evidence = OutcomeEvidence(
        evidence_id="ev_005",
        case_id="different_case_id",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        observed_at=now,
    )

    with pytest.raises(EntityMismatchError):
        await processor.process_outcome(
            evidence=mismatched_evidence,
            case=case,
            payment=payment,
        )


@pytest.mark.asyncio
async def test_terminal_case_cannot_process_new_outcome() -> None:
    """Case in terminal state (RECOVERED) cannot process new outcomes."""
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.CAPTURED)
    case = _sample_case(RecoveryCaseStatus.RECOVERED)
    now = datetime.now(UTC)

    evidence = OutcomeEvidence(
        evidence_id="ev_006",
        case_id="case_001",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.FAILED,
        observed_at=now,
    )

    with pytest.raises(TerminalCaseReopenError):
        await processor.process_outcome(
            evidence=evidence,
            case=case,
            payment=payment,
        )


def test_evidence_sanitization_removes_secrets_and_latent_truth() -> None:
    """OutcomeEvidence sanitizes sensitive keys and simulation latent truth from
    raw_details.
    """
    now = datetime.now(UTC)
    raw = {
        "key_secret": "super_secret_key",
        "authorization": "Bearer token_xyz",
        "potential_outcomes": {"RETRY": "SUCCESS"},
        "hidden_recoverability": 0.95,
        "oracle_action": "RETRY",
        "status": "failed",
        "safe_code": "BAD_REQUEST",
    }
    evidence = OutcomeEvidence(
        evidence_id="ev_sec_01",
        case_id="case_001",
        evidence_type=EvidenceType.PROVIDER_EVIDENCE,
        observed_at=now,
        raw_details=raw,
    )
    assert "key_secret" not in evidence.raw_details
    assert "authorization" not in evidence.raw_details
    assert "potential_outcomes" not in evidence.raw_details
    assert "hidden_recoverability" not in evidence.raw_details
    assert "oracle_action" not in evidence.raw_details
    assert evidence.raw_details["status"] == "failed"
    assert evidence.raw_details["safe_code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_positive_amount_without_verified_capture_is_not_recovered() -> None:
    """Remediation Guardrail 8: Positive amount without verified capture or
    verified provider recovery status must NOT be classified as RECOVERED.
    """
    processor = OutcomeProcessor()
    payment = _sample_payment(PaymentStatus.FAILED)
    case = _sample_case(RecoveryCaseStatus.OBSERVING)
    now = datetime.now(UTC)

    # Evidence has positive amount_recovered but payment_status is FAILED
    # and raw_details has no capture proof
    evidence = OutcomeEvidence(
        evidence_id="ev_unverified_amt",
        case_id="case_001",
        evidence_type=EvidenceType.PAYMENT_EVENT,
        payment_status=PaymentStatus.FAILED,
        amount_recovered=50000,
        observed_at=now,
    )

    res, updated_case, updated_payment = await processor.process_outcome(
        evidence=evidence,
        case=case,
        payment=payment,
    )

    assert res.outcome.type == OutcomeType.FAILED
    assert res.disposition == RecoveryLoopDisposition.RE_EVALUATE
    assert updated_case.status == RecoveryCaseStatus.EVALUATING
    assert updated_payment.status == PaymentStatus.FAILED
