"""Unit tests for decision-time feature snapshot generation (Phase 6)."""

from datetime import UTC, datetime

from apro.dataset.feature_snapshot import create_feature_snapshot
from apro.dataset.models import FeatureSnapshot
from apro.simulation.generator import ScenarioGenerator


def test_feature_snapshot_properties() -> None:
    """AC-04: Test feature snapshot creation and decision-time immutability."""
    scenario_gen = ScenarioGenerator()
    scenario = scenario_gen.generate(seed=1234)

    t_now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    snapshot = create_feature_snapshot(
        observable_state=scenario.observable_state,
        decision_timestamp=t_now,
        schema_version="feature-schema-v1",
    )

    assert isinstance(snapshot, FeatureSnapshot)
    assert snapshot.feature_schema_version == "feature-schema-v1"
    assert snapshot.decision_timestamp == "2026-06-01T12:00:00+00:00"
    assert snapshot.payment_amount == scenario.observable_state.payment.amount
    assert snapshot.payment_method == scenario.observable_state.payment.method
    assert snapshot.failure_code == scenario.observable_state.failure.failure_code
    assert snapshot.customer_id == scenario.observable_state.customer.customer_id
    assert snapshot.hour_of_day == scenario.observable_state.temporal.hour_of_day
    assert snapshot.candidate_actions == scenario.observable_state.candidate_actions


def test_feature_snapshot_has_no_hidden_state_attributes() -> None:
    """AC-04, AC-05: Ensure feature snapshot contains only observable fields."""
    scenario_gen = ScenarioGenerator()
    scenario = scenario_gen.generate(seed=555)

    snapshot = create_feature_snapshot(scenario.observable_state)
    snap_keys = set(snapshot.model_dump().keys())

    forbidden = {
        "recoverability",
        "customer_behavior",
        "true_failure_mechanism",
        "latent_customer_intent",
        "latent_bank_condition",
        "true_action_probabilities",
        "potential_outcomes",
        "best_achievable_action",
        "best_achievable_value",
        "outcome_status",
        "recovered_amount",
    }

    assert snap_keys.isdisjoint(forbidden)
