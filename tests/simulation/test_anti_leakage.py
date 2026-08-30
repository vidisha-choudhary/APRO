"""Anti-leakage and hidden/observable isolation tests for Phase 5."""

from apro.simulation.enums import (
    CustomerBehaviorClass,
    RecoverabilityClass,
    ScenarioDifficulty,
    SimulatedActionType,
    SimulatedOutcomeStatus,
)
from apro.simulation.generator import ScenarioGenerator
from apro.simulation.models import HiddenScenarioState, ObservableScenarioState


def test_hidden_fields_strictly_absent_from_observable_state() -> None:
    """AC-08, AC-09: Assert hidden fields are absent from ObservableScenarioState."""
    generator = ScenarioGenerator()
    scenario = generator.generate(seed=999)

    observable = scenario.to_observable_projection()
    assert isinstance(observable, ObservableScenarioState)

    obs_dict = observable.model_dump()

    # List of all forbidden ground-truth concepts
    forbidden_keys = [
        "recoverability",
        "customer_behavior",
        "true_failure_mechanism",
        "latent_customer_intent",
        "latent_bank_condition",
        "scenario_difficulty",
        "true_action_probabilities",
        "potential_outcomes",
        "outcome",
        "recovered_amount",
        "action_outcomes",
    ]

    def _assert_no_forbidden_key(d: dict[str, object], path: str = "") -> None:
        for k, v in d.items():
            current_path = f"{path}.{k}" if path else k
            assert k not in forbidden_keys, (
                f"Leakage! Forbidden key '{k}' found at '{current_path}'."
            )
            if isinstance(v, dict):
                _assert_no_forbidden_key(v, current_path)  # type: ignore[arg-type]

    _assert_no_forbidden_key(obs_dict)


def test_observable_projection_is_structurally_isolated() -> None:
    """AC-09: Confirm observable state is structurally isolated from hidden state."""
    generator = ScenarioGenerator()
    scenario = generator.generate(seed=123)

    obs = scenario.to_observable_projection()

    # Observable state attributes
    assert hasattr(obs, "customer")
    assert hasattr(obs, "payment")
    assert hasattr(obs, "failure")
    assert hasattr(obs, "temporal")
    assert hasattr(obs, "candidate_actions")

    # Observable state must NOT have hidden attributes
    assert not hasattr(obs, "recoverability")
    assert not hasattr(obs, "true_failure_mechanism")
    assert not hasattr(obs, "customer_behavior")
    assert not hasattr(obs, "latent_customer_intent")
    assert not hasattr(obs, "latent_bank_condition")
    assert not hasattr(obs, "true_action_probabilities")
    assert not hasattr(obs, "potential_outcomes")


def test_modifying_hidden_state_does_not_mutate_observable_projection() -> None:
    """AC-09: Test changing hidden ground truth does not affect observable view."""
    generator = ScenarioGenerator()
    scenario = generator.generate(seed=555)

    original_obs = scenario.to_observable_projection()

    # Create a modified hidden state
    mutated_hidden = HiddenScenarioState(
        true_failure_mechanism="MUTATED_SECRET_MECHANISM",
        recoverability=RecoverabilityClass.NON_RECOVERABLE,
        customer_behavior=CustomerBehaviorClass.LOW_RESPONSIVENESS,
        latent_customer_intent=0.01,
        latent_bank_condition=0.01,
        scenario_difficulty=ScenarioDifficulty.ADVERSARIAL,
        true_action_probabilities={SimulatedActionType.RETRY: 0.0},
        potential_outcomes={SimulatedActionType.RETRY: SimulatedOutcomeStatus.FAILURE},
    )

    mutated_scenario = scenario.model_copy(update={"hidden_state": mutated_hidden})

    # The observable projection of the mutated scenario remains identical
    assert mutated_scenario.to_observable_projection() == original_obs
    assert (
        mutated_scenario.to_observable_projection().model_dump()
        == original_obs.model_dump()
    )
