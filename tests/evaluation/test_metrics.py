"""Unit tests for metric computation and formulas (Phase 6)."""

from apro.evaluation.metrics import SafetyReliabilityMetrics, calculate_metrics
from apro.evaluation.traces import CaseEvaluationTrace
from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


def _make_trace(
    amount: int,
    recovered: int,
    action: SimulatedActionType,
    best_act: SimulatedActionType,
    best_val: int,
    status: SimulatedOutcomeStatus,
    is_unnec: bool = False,
) -> CaseEvaluationTrace:
    return CaseEvaluationTrace(
        case_id="c1",
        scenario_id="s1",
        strategy_name="test_strat",
        strategy_version="v1.0",
        dataset_version="d1",
        scenario_version="sc1",
        configuration_version="cf1",
        seed=42,
        payment_amount=amount,
        candidate_actions=[SimulatedActionType.RETRY, SimulatedActionType.STOP],
        chosen_action=action,
        outcome_status=status,
        recovered_amount=recovered,
        attempt_duration_seconds=10,
        best_achievable_action=best_act,
        best_achievable_value=best_val,
        regret=max(0, best_val - recovered),
        is_optimal=(action == best_act),
        is_intervention=(action != SimulatedActionType.STOP),
        is_unnecessary_intervention=is_unnec,
        decision_latency_ms=0.5,
        scenario_family=ScenarioFamily.TRANSIENT_FAILURE,
        recoverability=RecoverabilityClass.HIGHLY_RECOVERABLE,
        customer_behavior=CustomerBehaviorClass.NORMAL,
        scenario_difficulty=ScenarioDifficulty.EASY,
        payment_value_tier=PaymentValueTier.LOW_VALUE,
    )


def test_empty_traces_metric_calculation() -> None:
    """AC-15, AC-16: Test calculate_metrics handles empty batch without error."""
    metrics = calculate_metrics([])
    assert metrics.case_count == 0
    assert metrics.economic.revenue_at_risk == 0
    assert metrics.economic.revenue_recovered == 0
    assert metrics.economic.recovery_rate == 0.0
    assert metrics.economic.intervention_rate == 0.0
    assert metrics.decision.expected_value_capture == 1.0
    assert metrics.decision.total_regret == 0


def test_metric_calculations_formulas() -> None:
    """AC-15, AC-16: Test exact economic and decision metric formulas."""
    traces = [
        # Case 1: Recovered 1000 INR
        _make_trace(
            amount=100000,
            recovered=100000,
            action=SimulatedActionType.RETRY,
            best_act=SimulatedActionType.RETRY,
            best_val=100000,
            status=SimulatedOutcomeStatus.SUCCESS,
        ),
        # Case 2: Failed intervention (0 recovered)
        _make_trace(
            amount=200000,
            recovered=0,
            action=SimulatedActionType.RETRY,
            best_act=SimulatedActionType.PAYMENT_LINK,
            best_val=200000,
            status=SimulatedOutcomeStatus.FAILURE,
            is_unnec=False,
        ),
        # Case 3: Stopped (0 recovered, optimal because non-recoverable)
        _make_trace(
            amount=300000,
            recovered=0,
            action=SimulatedActionType.STOP,
            best_act=SimulatedActionType.STOP,
            best_val=0,
            status=SimulatedOutcomeStatus.FAILURE,
        ),
        # Case 4: Unnecessary intervention on 0 best_val
        _make_trace(
            amount=400000,
            recovered=0,
            action=SimulatedActionType.RETRY,
            best_act=SimulatedActionType.STOP,
            best_val=0,
            status=SimulatedOutcomeStatus.FAILURE,
            is_unnec=True,
        ),
    ]

    metrics = calculate_metrics(traces, baseline_revenue_recovered=50000)

    assert metrics.case_count == 4
    # Revenue at risk = 100k + 200k + 300k + 400k = 1,000,000 paise
    assert metrics.economic.revenue_at_risk == 1000000
    assert metrics.economic.revenue_recovered == 100000
    assert metrics.economic.incremental_revenue_recovered == 50000  # 100k - 50k
    assert metrics.economic.recovery_rate == 0.25  # 1 / 4
    assert metrics.economic.intervention_count == 3  # Cases 1, 2, 4
    assert metrics.economic.intervention_rate == 0.75  # 3 / 4
    assert metrics.economic.recovered_revenue_per_intervention == round(100000 / 3, 2)
    assert metrics.economic.unnecessary_intervention_count == 1
    assert metrics.economic.unnecessary_intervention_rate == 0.25  # 1 / 4
    assert metrics.economic.stop_count == 1
    assert metrics.economic.stop_rate == 0.25

    # Decision metrics
    assert metrics.decision.optimal_action_count == 2  # Cases 1 and 3
    assert metrics.decision.optimal_action_rate == 0.50  # 2 / 4
    # Total regret: Case 1=0, Case 2=200k, Case 3=0, Case 4=0 -> 200k
    assert metrics.decision.total_regret == 200000
    assert metrics.decision.average_regret == 50000.0  # 200k / 4
    # EV capture = 100k / (100k + 200k + 0 + 0) = 1/3 ~ 0.3333
    assert metrics.decision.expected_value_capture == round(100000 / 300000, 4)


def test_safety_reliability_metrics_schema() -> None:
    """Correction D: Test complete 13-field schema and None defaults."""
    sr = SafetyReliabilityMetrics(average_decision_latency_ms=0.045)
    d = sr.model_dump()

    required_fields = {
        "policy_violation_count",
        "duplicate_execution_count",
        "captured_payment_intervention_count",
        "retry_limit_violation_count",
        "invalid_model_execution_count",
        "unknown_state_unsafe_execution_count",
        "webhook_processing_success_rate",
        "event_deduplication_rate",
        "decision_success_rate",
        "execution_success_rate",
        "unknown_execution_rate",
        "api_error_rate",
        "average_decision_latency_ms",
    }

    assert set(d.keys()) == required_fields
    # Verify all future-phase fields default strictly to None
    for k in required_fields:
        if k != "average_decision_latency_ms":
            assert d[k] is None
    assert d["average_decision_latency_ms"] == 0.045
