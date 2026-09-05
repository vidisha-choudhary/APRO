"""Shared fixtures and test helpers for Phase 16 Dashboard tests."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import httpx
import pytest_asyncio

from apro.audit.enums import AuditEventType
from apro.audit.models import (
    AuditEvent,
    CaseAuditTrace,
    CycleTraceRecord,
    DecisionTraceRecord,
    ExecutionTraceRecord,
    OutcomeTraceRecord,
    PolicyTraceRecord,
)
from apro.dashboard.service import DashboardService
from apro.domain.enums import AuditActor
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.dataset import BenchmarkDatasetSnapshot
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.models import (
    BenchmarkCaseRecord,
    BenchmarkReport,
    OfflineEvaluationTruth,
)
from apro.evaluation.persistence import (
    PostgreSQLEvaluationArtifactStore,
)
from apro.main import app


def build_test_snapshot(
    dataset_id: str = "bench_snapshot_01",
    count: int = 20,
    recovery_modulo: int = 2,
    amount: int = 50000,
) -> BenchmarkDatasetSnapshot:
    """Build a deterministic BenchmarkDatasetSnapshot for testing."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    records = [
        BenchmarkCaseRecord(
            case_id=f"case_dash_{i}",
            payment_id=f"pay_dash_{i}",
            payment_amount=amount,
            currency="INR",
            payment_method="UPI" if i % 2 == 0 else "CARD",
            case_status="CLOSED_RECOVERED"
            if (i % recovery_modulo == 0)
            else "CLOSED_STOPPED",
            failure_code="GATEWAY_TIMEOUT" if i % 2 == 0 else "INSUFFICIENT_FUNDS",
            failure_category="TRANSIENT_SYSTEM"
            if i % 2 == 0
            else "CUSTOMER_ACTIONABLE",
            opened_at=now,
            closed_at=now,
            duration_seconds=20.0 + (i * 2.0),
            is_recovered=(i % recovery_modulo == 0),
            recovered_amount=amount if (i % recovery_modulo == 0) else 0,
            intervention_count=1 if (i % recovery_modulo == 0) else 0,
            final_action_type="RETRY" if i % 2 == 0 else "PAYMENT_LINK",
            offline_truth=OfflineEvaluationTruth(
                ground_truth_recovered=(i % recovery_modulo == 0),
                ground_truth_recovered_amount=amount
                if (i % recovery_modulo == 0)
                else 0,
                ground_truth_best_action="RETRY" if i % 2 == 0 else "PAYMENT_LINK",
                counterfactual_outcomes={
                    "RETRY": {
                        "status": "SUCCESS" if (i % 4 == 0) else "FAILURE",
                        "recovered_amount": amount if (i % 4 == 0) else 0,
                    },
                    "PAYMENT_LINK": {
                        "status": "SUCCESS" if (i % 3 == 0) else "FAILURE",
                        "recovered_amount": amount if (i % 3 == 0) else 0,
                    },
                    "ESCALATE": {
                        "status": "SUCCESS" if (i % 5 == 0) else "FAILURE",
                        "recovered_amount": amount if (i % 5 == 0) else 0,
                    },
                },
            ),
        )
        for i in range(count)
    ]
    return BenchmarkDatasetSnapshot.from_records(
        records, dataset_id=dataset_id, dataset_version="1.0.0"
    )


def generate_test_benchmark_report(
    run_id: str = "run_test_001",
    dataset_id: str = "bench_snapshot_01",
    count: int = 20,
    recovery_modulo: int = 2,
    amount: int = 50000,
    seed: int = 42,
    created_at: str | None = None,
    config: EvaluationConfig | None = None,
) -> BenchmarkReport:
    """Generate a fully evaluated Phase 15 BenchmarkReport."""
    snapshot = build_test_snapshot(
        dataset_id=dataset_id,
        count=count,
        recovery_modulo=recovery_modulo,
        amount=amount,
    )
    eval_cfg = config or EvaluationConfig(bootstrap_seed=seed, bootstrap_iterations=200)
    evaluator = APROEvaluator(config=eval_cfg)
    ts = created_at or datetime.now(UTC).isoformat()
    return evaluator.evaluate_dataset(
        snapshot,
        benchmark_run_id=run_id,
        created_at=ts,
    )


def build_test_case_trace(case_id: str = "case_dash_0") -> CaseAuditTrace:
    """Build a complete reconstructed CaseAuditTrace for testing."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    events = [
        AuditEvent(
            audit_event_id="ev_001",
            case_id=case_id,
            event_type=AuditEventType.CASE_CREATED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"initial_failure_code": "GATEWAY_TIMEOUT"},
        ),
        AuditEvent(
            audit_event_id="ev_002",
            case_id=case_id,
            event_type=AuditEventType.DIAGNOSIS_CREATED,
            actor=AuditActor.MODEL,
            timestamp=now,
            payload={"category": "TRANSIENT_SYSTEM", "confidence": 0.95},
        ),
        AuditEvent(
            audit_event_id="ev_003",
            case_id=case_id,
            event_type=AuditEventType.PREDICTION_CREATED,
            actor=AuditActor.MODEL,
            timestamp=now,
            payload={"recovery_probability": 0.85},
        ),
        AuditEvent(
            audit_event_id="ev_004",
            case_id=case_id,
            event_type=AuditEventType.DECISION_CREATED,
            actor=AuditActor.MODEL,
            timestamp=now,
            payload={"selected_action": "RETRY"},
        ),
        AuditEvent(
            audit_event_id="ev_005",
            case_id=case_id,
            event_type=AuditEventType.POLICY_DECISION_CREATED,
            actor=AuditActor.POLICY,
            timestamp=now,
            payload={"result": "PERMITTED", "effective_action": "RETRY"},
        ),
        AuditEvent(
            audit_event_id="ev_006",
            case_id=case_id,
            event_type=AuditEventType.EXECUTION_STARTED,
            actor=AuditActor.EXECUTOR,
            timestamp=now,
            payload={"action_type": "RETRY"},
        ),
        AuditEvent(
            audit_event_id="ev_007",
            case_id=case_id,
            event_type=AuditEventType.OUTCOME_PROCESSED,
            actor=AuditActor.SYSTEM,
            timestamp=now,
            payload={"type": "RECOVERED", "amount_recovered": 50000},
        ),
    ]

    cycles = [
        CycleTraceRecord(
            cycle_number=1,
            decision=DecisionTraceRecord(
                decision_id="dec_001",
                case_id=case_id,
                cycle_number=1,
                selected_action="RETRY",
                created_at=now,
            ),
            policy=PolicyTraceRecord(
                policy_decision_id="pol_001",
                case_id=case_id,
                decision_id="dec_001",
                policy_outcome="PERMITTED",
                effective_action="RETRY",
                reason_code="SAFE_RETRY",
                created_at=now,
            ),
            execution=ExecutionTraceRecord(
                execution_id="exec_001",
                case_id=case_id,
                action_id="act_001",
                execution_mode="MOCK",
                executor_name="mock_executor",
                status="SUCCEEDED",
                started_at=now,
                completed_at=now,
            ),
            outcome=OutcomeTraceRecord(
                outcome_id="out_001",
                case_id=case_id,
                execution_id="exec_001",
                outcome_type="RECOVERED",
                amount_recovered=50000,
                observed_at=now,
            ),
            events=events,
        )
    ]

    questions = {
        "Q1_what_happened": "Payment failed due to GATEWAY_TIMEOUT.",
        "Q2_why_interpreted": "Diagnosed as TRANSIENT_SYSTEM with 0.95 confidence.",
        "Q3_what_considered": "Evaluated candidate actions: RETRY, PAYMENT_LINK, STOP.",
        "Q4_what_recommended": "Economic engine recommended RETRY with highest expected utility.",
        "Q5_what_policy_allowed": "Policy engine permitted RETRY under rule SAFE_RETRY.",
        "Q6_what_executed": "Dispatched RETRY to payment gateway.",
        "Q7_what_happened_afterward": "Outcome verified as RECOVERED with ₹500.00 recovered.",
    }

    return CaseAuditTrace(
        case_id=case_id,
        trace_id="tr_001",
        final_case_status="CLOSED_RECOVERED",
        final_outcome_type="RECOVERED",
        total_amount_recovered=50000,
        cycles=cycles,
        events=events,
        reviewer_answers=questions,
    )


@pytest_asyncio.fixture
async def postgres_test_store() -> AsyncGenerator[
    PostgreSQLEvaluationArtifactStore, None
]:
    """Fixture providing a clean durable PostgreSQLEvaluationArtifactStore connected to test DB."""
    from sqlalchemy import text

    store = PostgreSQLEvaluationArtifactStore()
    try:
        async with store._session_factory() as session, session.begin():
            await session.execute(
                text("TRUNCATE TABLE evaluation_benchmark_reports CASCADE;")
            )
    except Exception:
        pass
    yield store


@pytest_asyncio.fixture
async def async_client(
    postgres_test_store: PostgreSQLEvaluationArtifactStore,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """AsyncClient configured with PostgreSQLEvaluationArtifactStore in same event loop."""
    app.state.dashboard_service = DashboardService(
        eval_store=postgres_test_store,
        allow_in_memory_for_testing=False,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
