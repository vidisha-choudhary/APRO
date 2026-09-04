"""Unit tests for Phase 15 Primary KPI formulas and invariants."""

from datetime import UTC, datetime

from apro.domain.enums import ExecutionMode, ExecutionStatus, OutcomeType
from apro.domain.models import Execution, Outcome
from apro.evaluation.config import EvaluationConfig
from apro.evaluation.metrics import compute_primary_kpis
from apro.evaluation.models import BenchmarkCaseRecord


def test_empty_cases_primary_kpis() -> None:
    """AC-15, AC-20: Test compute_primary_kpis with empty case list."""
    cfg = EvaluationConfig()
    kpis = compute_primary_kpis([], cfg)

    assert kpis.case_count == 0
    assert kpis.eligible_cases == 0
    assert kpis.recovered_cases == 0
    assert kpis.recovery_rate == 0.0
    assert kpis.gross_recovered_amount == 0
    assert kpis.cost_per_recovered_rupee is None
    assert kpis.net_recovery_efficiency == 0.0


def test_primary_kpi_formulas() -> None:
    """AC-09, AC-11, AC-13, AC-14: Test recovery rate, gross/net revenue, cost."""
    cfg = EvaluationConfig()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # Case 1: Recovered 1000 INR (100,000 paise) via 1 RETRY (cost 100 paise)
    c1 = BenchmarkCaseRecord(
        case_id="c1",
        payment_id="p1",
        payment_amount=100000,
        opened_at=now,
        is_recovered=True,
        recovered_amount=100000,
        duration_seconds=10.0,
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
        outcomes=[
            Outcome(
                outcome_id="o1",
                case_id="c1",
                execution_id="e1",
                type=OutcomeType.RECOVERED,
                amount_recovered=100000,
                observed_at=now,
            )
        ],
    )

    # Case 2: Failed after 1 RETRY (cost 100 paise)
    c2 = BenchmarkCaseRecord(
        case_id="c2",
        payment_id="p2",
        payment_amount=200000,
        opened_at=now,
        is_recovered=False,
        recovered_amount=0,
        executions=[
            Execution(
                execution_id="e2",
                action_id="a2",
                case_id="c2",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.FAILED,
                started_at=now,
            )
        ],
        outcomes=[
            Outcome(
                outcome_id="o2",
                case_id="c2",
                execution_id="e2",
                type=OutcomeType.FAILED,
                amount_recovered=0,
                observed_at=now,
            )
        ],
    )

    # Case 3: Stopped (0 cost, 0 recovered)
    c3 = BenchmarkCaseRecord(
        case_id="c3",
        payment_id="p3",
        payment_amount=300000,
        case_status="CLOSED_STOPPED",
        opened_at=now,
        is_recovered=False,
        recovered_amount=0,
        executions=[],
        outcomes=[],
    )

    kpis = compute_primary_kpis([c1, c2, c3], cfg)

    assert kpis.eligible_cases == 3
    assert kpis.recovered_cases == 1
    assert kpis.recovery_rate == round(1 / 3, 4)
    assert kpis.eligible_at_risk_amount == 600000
    assert kpis.gross_recovered_amount == 100000
    assert kpis.recovered_revenue_rate == round(100000 / 600000, 4)
    # Cost = 100 + 100 + 0 = 200 paise (₹2.00)
    assert kpis.total_intervention_cost == 200
    # Net = 100000 - 200 = 99800 paise
    assert kpis.net_recovered_revenue == 99800
    # Cost per recovered rupee = 200 / 100000 = 0.0020
    assert kpis.cost_per_recovered_rupee == 0.0020
    assert kpis.net_recovery_efficiency == round(99800 / 600000, 4)
    assert kpis.mean_time_to_recovery_seconds == 10.0


def test_succeeded_execution_without_recovery_evidence_not_counted() -> None:
    """AC-10: ExecutionStatus.SUCCEEDED without RECOVERED outcome != RECOVERED."""
    cfg = EvaluationConfig()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    # Execution succeeded (e.g. payment link created/sent) but customer never paid
    c_pending = BenchmarkCaseRecord(
        case_id="c_pend",
        payment_id="p_pend",
        payment_amount=100000,
        case_status="OPEN",
        opened_at=now,
        is_recovered=False,
        recovered_amount=0,
        executions=[
            Execution(
                execution_id="e_pend",
                action_id="a_pend",
                case_id="c_pend",
                execution_type="PAYMENT_LINK",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,  # Transport succeeded
                started_at=now,
            )
        ],
        outcomes=[
            Outcome(
                outcome_id="o_pend",
                case_id="c_pend",
                execution_id="e_pend",
                type=OutcomeType.PENDING,  # Outcome is pending, not recovered
                amount_recovered=0,
                observed_at=now,
            )
        ],
    )

    kpis = compute_primary_kpis([c_pending], cfg)
    assert kpis.recovered_cases == 0
    assert kpis.recovery_rate == 0.0
    assert kpis.gross_recovered_amount == 0


def test_duplicate_outcomes_do_not_double_count_revenue() -> None:
    """AC-11: Duplicate outcome records must not double-count revenue."""
    cfg = EvaluationConfig()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    c_dup_out = BenchmarkCaseRecord(
        case_id="c_dup",
        payment_id="p_dup",
        payment_amount=100000,
        opened_at=now,
        is_recovered=True,
        recovered_amount=100000,
        executions=[
            Execution(
                execution_id="e1",
                action_id="a1",
                case_id="c_dup",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.SUCCEEDED,
                started_at=now,
            )
        ],
        outcomes=[
            Outcome(
                outcome_id="o1",
                case_id="c_dup",
                execution_id="e1",
                type=OutcomeType.RECOVERED,
                amount_recovered=100000,
                observed_at=now,
            ),
            Outcome(  # Duplicate outcome record with same ID
                outcome_id="o1",
                case_id="c_dup",
                execution_id="e1",
                type=OutcomeType.RECOVERED,
                amount_recovered=100000,
                observed_at=now,
            ),
        ],
    )

    kpis = compute_primary_kpis([c_dup_out], cfg)
    assert kpis.gross_recovered_amount == 100000  # Not 200,000


def test_zero_revenue_cost_per_recovered_rupee_undefined() -> None:
    """AC-15: Zero recovered revenue returns None / safe undefined state."""
    cfg = EvaluationConfig()
    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

    c_fail = BenchmarkCaseRecord(
        case_id="c_fail",
        payment_id="p_fail",
        payment_amount=100000,
        opened_at=now,
        is_recovered=False,
        recovered_amount=0,
        executions=[
            Execution(
                execution_id="e1",
                action_id="a1",
                case_id="c_fail",
                execution_type="RETRY",
                execution_mode=ExecutionMode.SIMULATION,
                status=ExecutionStatus.FAILED,
                started_at=now,
            )
        ],
    )

    kpis = compute_primary_kpis([c_fail], cfg)
    assert kpis.gross_recovered_amount == 0
    assert kpis.cost_per_recovered_rupee is None
