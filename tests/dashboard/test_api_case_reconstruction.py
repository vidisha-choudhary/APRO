"""Tests for Case Explorer and Phase 14 Case Reconstruction endpoints."""

from datetime import UTC
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from apro.audit.reconstruction import CaseReconstructionService
from tests.dashboard.conftest import build_test_case_trace


@pytest.mark.asyncio
async def test_case_explorer_list(async_client: httpx.AsyncClient) -> None:
    """AC-08, AC-51, AC-52: Test case listing endpoint with pagination."""
    response = await async_client.get("/api/dashboard/cases?page=1&page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "items" in body
    assert body["page"] == 1
    assert body["page_size"] == 10


@pytest.mark.asyncio
async def test_case_detail_reconstruction(async_client: httpx.AsyncClient) -> None:
    """AC-08, AC-25, AC-27, AC-28, AC-29, AC-30, AC-31, AC-32, AC-33, AC-34: Test full case reconstruction."""
    trace = build_test_case_trace("case_recon_001")

    with patch.object(
        CaseReconstructionService, "reconstruct_case", new=AsyncMock(return_value=trace)
    ):
        response = await async_client.get("/api/dashboard/cases/case_recon_001")
        assert response.status_code == 200
        body = response.json()

        assert body["status"] == "ok"
        case_data = body["case"]
        assert case_data["case_id"] == "case_recon_001"
        assert case_data["final_case_status"] == "CLOSED_RECOVERED"
        assert case_data["completeness"] == "COMPLETE"
        assert len(case_data["cycles"]) >= 1


@pytest.mark.asyncio
async def test_case_timeline_ordering(async_client: httpx.AsyncClient) -> None:
    """AC-09, AC-26: Test chronological audit events timeline endpoint."""
    trace = build_test_case_trace("case_timeline_001")

    with patch.object(
        CaseReconstructionService, "reconstruct_case", new=AsyncMock(return_value=trace)
    ):
        response = await async_client.get(
            "/api/dashboard/cases/case_timeline_001/timeline"
        )
        assert response.status_code == 200
        body = response.json()

        assert body["status"] == "ok"
        assert body["case_id"] == "case_timeline_001"
        assert len(body["events"]) == len(trace.events)
        assert body["events"][0]["event_type"] == "CASE_CREATED"
        assert body["events"][-1]["event_type"] == "OUTCOME_PROCESSED"


@pytest.mark.asyncio
async def test_reviewer_seven_questions(async_client: httpx.AsyncClient) -> None:
    """AC-10: Test Q1–Q7 reviewer questions retrieved from backend reconstruction."""
    trace = build_test_case_trace("case_q_001")

    with patch.object(
        CaseReconstructionService, "reconstruct_case", new=AsyncMock(return_value=trace)
    ):
        response = await async_client.get(
            "/api/dashboard/cases/case_q_001/reviewer-questions"
        )
        assert response.status_code == 200
        body = response.json()

        assert body["status"] == "ok"
        assert body["case_id"] == "case_q_001"
        assert body["completeness"] == "COMPLETE"
        assert body["integrity_valid"] is True

        q = body["questions"]
        assert "Q1_what_happened" in q
        assert "Q2_why_interpreted" in q
        assert "Q3_what_considered" in q
        assert "Q4_what_recommended" in q
        assert "Q5_what_policy_allowed" in q
        assert "Q6_what_executed" in q
        assert "Q7_what_happened_afterward" in q


@pytest.mark.asyncio
async def test_case_not_found_yields_404(async_client: httpx.AsyncClient) -> None:
    """Test unknown case ID returns 404."""
    from apro.audit.exceptions import AuditNotFoundError

    with patch.object(
        CaseReconstructionService,
        "reconstruct_case",
        new=AsyncMock(side_effect=AuditNotFoundError("No audit records found")),
    ):
        res = await async_client.get("/api/dashboard/cases/case_nonexistent")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_real_postgres_case_reconstruction(
    async_client: httpx.AsyncClient,
) -> None:
    """AC-08, AC-09, AC-10 / Requirement 9: Real PostgreSQL case reconstruction without mocks."""
    import os
    import uuid
    from datetime import datetime

    from apro.audit.enums import AuditEventType
    from apro.config import settings
    from apro.domain.enums import (
        AuditActor,
        ExecutionMode,
        ExecutionStatus,
        FailureCategory,
        OutcomeType,
        PaymentStatus,
        PolicyDecisionResult,
        RecoveryActionType,
        RecoveryCaseStatus,
    )
    from apro.persistence.database import get_async_engine, get_session_factory
    from apro.persistence.models import (
        AuditEventModel,
        CustomerModel,
        DecisionModel,
        DiagnosisModel,
        ExecutionModel,
        OutcomeModel,
        PaymentModel,
        PolicyDecisionModel,
        RecoveryActionModel,
        RecoveryCaseModel,
    )

    db_url = os.environ.get("POSTGRES_TEST_URL") or settings.DATABASE_URL
    engine = get_async_engine(db_url)
    factory = get_session_factory(engine)

    now = datetime.now(UTC)
    cust_id = str(uuid.uuid4())
    payment_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    act_id = str(uuid.uuid4())
    diag_id = str(uuid.uuid4())
    dec_id = str(uuid.uuid4())
    pdec_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    out_id = str(uuid.uuid4())

    async with factory() as session:
        # Create Customer
        cust = CustomerModel(
            customer_id=cust_id,
            created_at=now,
            updated_at=now,
        )
        session.add(cust)
        await session.flush()

        # Create Payment
        pay = PaymentModel(
            payment_id=payment_id,
            customer_id=cust_id,
            provider="RAZORPAY",
            amount=75000,
            currency="INR",
            method="card",
            status=PaymentStatus.FAILED.value,
            created_at=now,
            updated_at=now,
        )
        session.add(pay)
        await session.flush()

        # Create Recovery Case
        case = RecoveryCaseModel(
            case_id=case_id,
            payment_id=payment_id,
            customer_id=cust_id,
            status=RecoveryCaseStatus.RECOVERED.value,
            opened_at=now,
            closed_at=now,
            updated_at=now,
            recovery_amount=75000,
        )
        session.add(case)
        await session.flush()

        # Create Recovery Action
        act = RecoveryActionModel(
            action_id=act_id,
            case_id=case_id,
            action_type="RETRY",
            status="APPROVED",
            created_at=now,
            updated_at=now,
        )
        session.add(act)

        # Create Diagnosis
        diag = DiagnosisModel(
            diagnosis_id=diag_id,
            case_id=case_id,
            category=FailureCategory.TRANSIENT.value,
            confidence=0.95,
            evidence=["GATEWAY_TIMEOUT"],
            model_name="diag_v1",
            model_version="1.0.0",
            created_at=now,
        )
        session.add(diag)

        # Create Decision
        dec = DecisionModel(
            decision_id=dec_id,
            case_id=case_id,
            recommended_action=RecoveryActionType.RETRY.value,
            confidence=0.95,
            expected_recovery_value=75000,
            reason="High expected value retry",
            model_name="dec_v1",
            model_version="1.0.0",
            created_at=now,
        )
        session.add(dec)
        await session.flush()

        # Create Policy Decision
        pdec = PolicyDecisionModel(
            policy_decision_id=pdec_id,
            decision_id=dec_id,
            case_id=case_id,
            result=PolicyDecisionResult.ALLOW.value,
            reason="Safe retry policy permitted",
            policy_version="1.0.0",
            created_at=now,
        )
        session.add(pdec)

        # Create Execution
        exc = ExecutionModel(
            execution_id=exec_id,
            action_id=act_id,
            case_id=case_id,
            execution_type="RETRY",
            execution_mode=ExecutionMode.RAZORPAY_TEST_MODE.value,
            status=ExecutionStatus.SUCCEEDED.value,
            idempotency_key=f"idem_{case_id}",
            started_at=now,
            completed_at=now,
        )
        session.add(exc)
        await session.flush()

        # Create Outcome
        out = OutcomeModel(
            outcome_id=out_id,
            case_id=case_id,
            execution_id=exec_id,
            type=OutcomeType.RECOVERED.value,
            amount_recovered=75000,
            evidence_reference="out_ref_01",
            observed_at=now,
        )
        session.add(out)
        await session.flush()

        # Create Canonical Audit Events for reconstruction
        events_data = [
            (
                str(uuid.uuid4()),
                AuditEventType.CASE_CREATED.value,
                AuditActor.SYSTEM.value,
                {
                    "payment_id": payment_id,
                    "amount": 75000,
                    "initial_failure_code": "GATEWAY_TIMEOUT",
                },
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.DIAGNOSIS_CREATED.value,
                AuditActor.MODEL.value,
                {"failure_category": "TRANSIENT_SYSTEM", "confidence": 0.95},
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.PREDICTION_CREATED.value,
                AuditActor.MODEL.value,
                {"recovery_probability": 0.85},
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.DECISION_CREATED.value,
                AuditActor.MODEL.value,
                {"selected_action": "RETRY", "expected_recovery_value": 75000},
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.POLICY_DECISION_CREATED.value,
                AuditActor.POLICY.value,
                {
                    "result": "PERMITTED",
                    "effective_action": "RETRY",
                    "policy_outcome": "PERMITTED",
                },
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.EXECUTION_STARTED.value,
                AuditActor.EXECUTOR.value,
                {"action_type": "RETRY", "execution_id": exec_id},
            ),
            (
                str(uuid.uuid4()),
                AuditEventType.OUTCOME_PROCESSED.value,
                AuditActor.SYSTEM.value,
                {
                    "outcome_type": "RECOVERED",
                    "amount_recovered": 75000,
                    "type": "RECOVERED",
                },
            ),
        ]

        from datetime import timedelta

        for idx, (evt_id, evt_type, actor, payload) in enumerate(events_data):
            evt = AuditEventModel(
                audit_event_id=evt_id,
                case_id=case_id,
                event_type=evt_type,
                actor=actor,
                timestamp=now + timedelta(seconds=idx),
                payload=payload,
                correlation_id="corr_real_01",
            )
            session.add(evt)

        await session.commit()

        # Call Dashboard API without any mock of CaseReconstructionService
        res_detail = await async_client.get(f"/api/dashboard/cases/{case_id}")
        assert res_detail.status_code == 200
        detail_body = res_detail.json()
    assert detail_body["status"] == "ok"
    assert detail_body["case"]["case_id"] == case_id
    assert detail_body["case"]["completeness"] == "COMPLETE"
    assert detail_body["case"]["integrity_valid"] is True

    # Call Timeline
    res_timeline = await async_client.get(f"/api/dashboard/cases/{case_id}/timeline")
    assert res_timeline.status_code == 200
    timeline_body = res_timeline.json()
    assert len(timeline_body["events"]) == 7
    assert timeline_body["events"][0]["event_type"] == "CASE_CREATED"
    assert timeline_body["events"][-1]["event_type"] == "OUTCOME_PROCESSED"

    # Call Reviewer Questions
    res_q = await async_client.get(f"/api/dashboard/cases/{case_id}/reviewer-questions")
    assert res_q.status_code == 200
    q_body = res_q.json()
    assert q_body["completeness"] == "COMPLETE"
    assert q_body["integrity_valid"] is True
    questions = q_body["questions"]
    assert "Q1_what_happened" in questions
    assert "Q2_why_interpreted" in questions
    assert "Q3_what_considered" in questions
    assert "Q4_what_recommended" in questions
    assert "Q5_what_policy_allowed" in questions
    assert "Q6_what_executed" in questions
    assert "Q7_what_happened_afterward" in questions

    await engine.dispose()


@pytest.mark.asyncio
async def test_case_list_zero_cases_and_db_failure(
    async_client: httpx.AsyncClient,
) -> None:
    """AC-51 / Requirement 5: Valid DB with 0 cases returns 200; DB failure returns 503."""
    from apro.dashboard.service import DashboardService
    from apro.evaluation.exceptions import EvaluationPersistenceError
    from apro.main import app

    # 1. Valid DB with zero matching cases -> 200 with items=[] and total_count=0
    res_zero = await async_client.get(
        "/api/dashboard/cases?status=NON_EXISTENT_STATUS_999"
    )
    assert res_zero.status_code == 200
    zero_body = res_zero.json()
    assert zero_body["status"] == "ok"
    assert zero_body["items"] == []
    assert zero_body["total_count"] == 0

    # 2. Database failure -> HTTP 503 EvaluationPersistenceError
    class BrokenUOWFactory:
        def __call__(self) -> None:
            raise RuntimeError("PostgreSQL connection refused / broken socket")

    saved_service = getattr(app.state, "dashboard_service", None)
    try:
        broken_service = DashboardService(
            uow_factory=BrokenUOWFactory(),
            allow_in_memory_for_testing=True,
        )
        app.state.dashboard_service = broken_service

        res_fail = await async_client.get("/api/dashboard/cases")
        assert res_fail.status_code == 503
        assert "Database" in res_fail.json()["detail"] or "503" in str(
            res_fail.status_code
        )

        with pytest.raises(EvaluationPersistenceError):
            await broken_service.list_cases()
    finally:
        app.state.dashboard_service = saved_service
