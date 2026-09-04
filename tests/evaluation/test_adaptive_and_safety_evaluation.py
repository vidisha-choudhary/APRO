"""Unit tests for Phase 13 adaptive loop metrics and safety KPIs (Phase 15)."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, PolicyDecisionResult
from apro.domain.models import Execution, PolicyDecision
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.evaluator import APROEvaluator
from apro.evaluation.metrics import compute_safety_kpis
from apro.evaluation.models import BenchmarkCaseRecord


def test_adaptive_loop_metrics_reconstruction() -> None:
    """AC-51, AC-52, AC-53, AC-54: Single vs multi-cycle recovery."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # Case 1: Single cycle recovery
    c1 = BenchmarkCaseRecord(
        case_id="c1",
        payment_id="p1",
        payment_amount=100000,
        opened_at=now,
        case_status="CLOSED_RECOVERED",
        is_recovered=True,
        recovered_amount=100000,
        cycle_count=1,
        executions=[
            Execution(
                execution_id="e1",
                action_id="a1",
                case_id="c1",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,
                started_at=now,
            )
        ],
    )

    # Case 2: Multi-cycle adaptive recovery (Cycle 1 RETRY -> Cycle 2 LINK)
    c2 = BenchmarkCaseRecord(
        case_id="c2",
        payment_id="p2",
        payment_amount=200000,
        opened_at=now,
        case_status="CLOSED_RECOVERED",
        is_recovered=True,
        recovered_amount=200000,
        cycle_count=2,
        re_evaluation_count=1,
        executions=[
            Execution(
                execution_id="e2_1",
                action_id="a2_1",
                case_id="c2",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.FAILED,
                started_at=now,
            ),
            Execution(
                execution_id="e2_2",
                action_id="a2_2",
                case_id="c2",
                execution_type="PAYMENT_LINK",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,
                started_at=now,
            ),
        ],
    )

    evaluator = APROEvaluator(EvaluationConfig())
    ad = evaluator._evaluate_adaptive_loop([c1, c2])

    assert ad.total_cases == 2
    assert ad.single_cycle_recovery_count == 1
    assert ad.single_cycle_recovery_rate == 0.50
    assert ad.multi_cycle_recovery_count == 1
    assert ad.multi_cycle_recovery_rate == 0.50
    assert ad.recovery_after_re_evaluation_rate == 1.0
    assert ad.incremental_recovery_after_first_failure == 1.0
    assert ad.same_action_avoidance_rate == 1.0  # Chose PAYMENT_LINK after RETRY
    assert ad.bounded_termination_rate == 1.0


def test_safety_kpis_and_zero_violation_invariants() -> None:
    """AC-59, AC-60, AC-61, AC-62: Test safety KPIs, zero unsafe dispatch invariant."""
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # Clean case with policy decision and authorized execution
    c_clean = BenchmarkCaseRecord(
        case_id="c_clean",
        payment_id="p_clean",
        payment_amount=100000,
        opened_at=now,
        policy_decisions=[
            PolicyDecision(
                policy_decision_id="pd1",
                decision_id="d1",
                case_id="c_clean",
                result=PolicyDecisionResult.ALLOW,
                reason="Policy approved",
                policy_version="1.0",
                created_at=now,
            )
        ],
        executions=[
            Execution(
                execution_id="e1",
                action_id="a1",
                case_id="c_clean",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,
                started_at=now,
            )
        ],
    )

    # Policy blocked case
    c_blocked = BenchmarkCaseRecord(
        case_id="c_block",
        payment_id="p_block",
        payment_amount=100000,
        opened_at=now,
        case_status="CLOSED_STOPPED",
        policy_decisions=[
            PolicyDecision(
                policy_decision_id="pd2",
                decision_id="d2",
                case_id="c_block",
                result=PolicyDecisionResult.BLOCK,
                reason="State_guard reject: retry limit reached",
                policy_version="1.0",
                created_at=now,
            )
        ],
        executions=[],
    )

    safety = compute_safety_kpis([c_clean, c_blocked])

    assert safety.policy_block_count == 1
    assert safety.policy_block_rate == 0.50
    assert safety.state_guard_rejection_count == 1
    assert safety.unsafe_dispatch_count == 0
    assert safety.unsafe_dispatch_rate == 0.0
    assert safety.policy_bypass_count == 0
    assert safety.duplicate_execution_attempt_count == 0
