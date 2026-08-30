"""Unit and integration tests for independent OutcomeEngine (Phase 5)."""

import inspect
from typing import Any

import pytest

from apro.simulation.engine import OutcomeEngine
from apro.simulation.enums import (
    SimulatedActionType,
    SimulatedOutcomeStatus,
)
from apro.simulation.generator import ScenarioGenerator
from apro.simulation.models import SimulatedActionOutcome


def test_outcome_generation_all_actions() -> None:
    """AC-10, AC-11: Test outcome generation across all candidate actions."""
    generator = ScenarioGenerator()
    engine = OutcomeEngine()

    scenario = generator.generate(seed=777)

    valid_statuses = {
        SimulatedOutcomeStatus.SUCCESS,
        SimulatedOutcomeStatus.FAILURE,
        SimulatedOutcomeStatus.PENDING,
    }

    for action in scenario.observable_state.candidate_actions:
        outcome = engine.generate_outcome(scenario, action)
        assert isinstance(outcome, SimulatedActionOutcome)
        assert outcome.scenario_id == scenario.scenario_id
        assert outcome.action == action
        assert outcome.status in valid_statuses
        assert outcome.attempt_duration_seconds >= 0
        if outcome.status == SimulatedOutcomeStatus.SUCCESS:
            assert outcome.recovered_amount == scenario.observable_state.payment.amount
        else:
            assert outcome.recovered_amount == 0


def test_outcome_deterministic_reproducibility() -> None:
    """AC-12: Test identical scenario + action + outcome seed produces same outcome."""
    generator = ScenarioGenerator()
    engine = OutcomeEngine()

    scenario = generator.generate(seed=12345)

    outcome_1 = engine.generate_outcome(
        scenario, SimulatedActionType.RETRY, outcome_seed=42
    )
    outcome_2 = engine.generate_outcome(
        scenario, SimulatedActionType.RETRY, outcome_seed=42
    )

    assert outcome_1 == outcome_2
    assert outcome_1.status == outcome_2.status
    assert outcome_1.recovered_amount == outcome_2.recovered_amount
    assert outcome_1.attempt_duration_seconds == outcome_2.attempt_duration_seconds


def test_outcome_engine_signature_excludes_apro_predictions() -> None:
    """AC-11, AC-17: Verify OutcomeEngine API signature cannot accept APRO scores."""
    engine = OutcomeEngine()
    sig = inspect.signature(engine.generate_outcome)

    param_names = list(sig.parameters.keys())
    assert "scenario" in param_names
    assert "chosen_action" in param_names
    assert "outcome_seed" in param_names

    forbidden_param_substrings = [
        "pred",
        "score",
        "prob",
        "model",
        "decision",
        "erv",
        "confidence",
        "recommendation",
        "apro",
    ]

    for param in param_names:
        for forbidden in forbidden_param_substrings:
            assert forbidden not in param.lower(), (
                f"Forbidden parameter '{param}' found in OutcomeEngine signature!"
            )


def test_outcome_independence_from_external_predictions() -> None:
    """AC-11 (Correction A): Show outcome is invariant to external APRO values."""
    generator = ScenarioGenerator()
    engine = OutcomeEngine()

    scenario = generator.generate(seed=888)

    # Stand-in dummy APRO predictions representing two opposite model inferences
    standin_apro_high: dict[str, Any] = {
        "predicted_probability": 0.99,
        "expected_recovery_value": 50000,
        "confidence": 0.98,
        "recommended_action": "RETRY",
    }
    standin_apro_low: dict[str, Any] = {
        "predicted_probability": 0.01,
        "expected_recovery_value": 0,
        "confidence": 0.10,
        "recommended_action": "STOP",
    }

    # Verify dummy values are distinct
    assert standin_apro_high != standin_apro_low

    def evaluate_with_external_prediction(
        external_prediction: dict[str, Any],
    ) -> SimulatedActionOutcome:
        # The external prediction is part of caller context but intentionally
        # NOT passed into the OutcomeEngine API.
        assert external_prediction["predicted_probability"] in (0.99, 0.01)
        return engine.generate_outcome(
            scenario,
            SimulatedActionType.RETRY,
            outcome_seed=100,
        )

    outcome_high = evaluate_with_external_prediction(standin_apro_high)
    outcome_low = evaluate_with_external_prediction(standin_apro_low)

    # Outcomes must be exactly identical despite opposite external stand-in values
    assert outcome_high == outcome_low
    assert outcome_high.status == outcome_low.status
    assert outcome_high.recovered_amount == outcome_low.recovered_amount


def test_potential_outcome_matches_realized_default_outcome() -> None:
    """AC-11, AC-12 (Correction C): Verify potential outcome equals realized default."""
    generator = ScenarioGenerator()
    engine = OutcomeEngine()

    # Test across multiple seeds and all candidate actions
    for seed in [42, 101, 2026, 9999]:
        scenario = generator.generate(seed=seed)
        for action in scenario.observable_state.candidate_actions:
            stored_potential = scenario.hidden_state.potential_outcomes[action]

            # Realized outcome under default ground-truth semantics
            realized_outcome = engine.generate_outcome(
                scenario, action, outcome_seed=None
            )

            assert realized_outcome.status == stored_potential, (
                f"Mismatch for seed {seed}, action {action}: "
                f"realized={realized_outcome.status}, potential={stored_potential}"
            )


def test_invalid_action_raises_explicit_error() -> None:
    """AC-16: Test unsupported/invalid action raises explicit ValueError."""
    generator = ScenarioGenerator()
    engine = OutcomeEngine()

    scenario = generator.generate(seed=333)

    # Mutate candidate actions to simulate an action not allowed for this scenario
    restricted_obs = scenario.observable_state.model_copy(
        update={"candidate_actions": [SimulatedActionType.RETRY]}
    )
    restricted_scenario = scenario.model_copy(
        update={"observable_state": restricted_obs}
    )

    with pytest.raises(ValueError, match="is not in candidate actions"):
        engine.generate_outcome(restricted_scenario, SimulatedActionType.PAYMENT_LINK)
