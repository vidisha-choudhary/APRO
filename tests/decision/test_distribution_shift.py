"""Unit tests for distribution shift comparison in decision evaluation."""

from apro.decision.evaluation import (
    DecisionEvaluationMetrics,
    EconomicDecisionEvaluator,
)


def test_distribution_shift_comparison() -> None:
    """Verify delta computation between in-distribution and shifted benchmarks."""
    m_in = DecisionEvaluationMetrics(
        case_count=100,
        decision_accuracy_vs_oracle=0.75,
        mean_utility=50000.0,
        median_utility=48000.0,
        mean_decision_regret=12000.0,
        median_decision_regret=10000.0,
        oracle_gap=8000.0,
        recovery_rate=0.70,
        total_recovered_amount=3500000,
        mean_recovered_amount=35000.0,
        intervention_rate=0.80,
        no_intervention_rate=0.20,
        unnecessary_intervention_rate=0.05,
        ineligible_selection_rate=0.0,
        constraint_violation_count=0,
        selected_action_distribution={"RETRY": 50, "PAYMENT_LINK": 30, "STOP": 20},
    )

    m_shift = DecisionEvaluationMetrics(
        case_count=100,
        decision_accuracy_vs_oracle=0.72,
        mean_utility=46000.0,
        median_utility=44000.0,
        mean_decision_regret=14000.0,
        median_decision_regret=12000.0,
        oracle_gap=9000.0,
        recovery_rate=0.68,
        total_recovered_amount=3200000,
        mean_recovered_amount=32000.0,
        intervention_rate=0.82,
        no_intervention_rate=0.18,
        unnecessary_intervention_rate=0.06,
        ineligible_selection_rate=0.0,
        constraint_violation_count=0,
        selected_action_distribution={"RETRY": 48, "PAYMENT_LINK": 34, "STOP": 18},
    )

    evaluator = EconomicDecisionEvaluator()
    comp = evaluator.compare_distribution_shift(m_in, m_shift)

    deltas = comp["deltas"]
    assert deltas["decision_accuracy_delta"] == round(0.72 - 0.75, 4)
    assert deltas["mean_utility_delta"] == round(46000.0 - 50000.0, 2)
    assert deltas["mean_regret_delta"] == round(14000.0 - 12000.0, 2)
    assert deltas["recovery_rate_delta"] == round(0.68 - 0.70, 4)
