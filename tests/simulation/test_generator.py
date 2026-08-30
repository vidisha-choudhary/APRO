"""Unit and integration tests for ScenarioGenerator (Phase 5)."""

from apro.simulation.config import SimulationConfig
from apro.simulation.enums import (
    CustomerBehaviorClass,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedPaymentMethod,
)
from apro.simulation.generator import ScenarioGenerator
from apro.simulation.models import SimulationScenario


def test_scenario_generation_basic_properties() -> None:
    """AC-01, AC-02, AC-03, AC-04: Test valid scenario generation and metadata."""
    generator = ScenarioGenerator()
    seed = 42
    scenario = generator.generate(seed)

    assert isinstance(scenario, SimulationScenario)
    assert scenario.scenario_id.startswith("scen_")
    assert scenario.generation_seed == 42
    assert scenario.scenario_version == "scenario-v1"
    assert scenario.configuration_version == "config-v1"
    assert isinstance(scenario.scenario_family, ScenarioFamily)

    # Observable state checks
    obs = scenario.observable_state
    assert obs.scenario_id == scenario.scenario_id
    assert obs.payment.amount > 0
    assert obs.payment.currency == "INR"
    assert isinstance(obs.payment.method, SimulatedPaymentMethod)
    assert obs.failure.failure_reason != ""
    assert obs.failure.failure_code != ""
    assert 0 <= obs.temporal.hour_of_day <= 23
    assert 0 <= obs.temporal.day_of_week <= 6
    assert isinstance(obs.temporal.is_weekend, bool)

    # Candidate actions checks (AC-10)
    expected_actions = [
        SimulatedActionType.RETRY,
        SimulatedActionType.PAYMENT_LINK,
        SimulatedActionType.OUTREACH,
        SimulatedActionType.STOP,
        SimulatedActionType.ESCALATE,
    ]
    assert obs.candidate_actions == expected_actions


def test_deterministic_reproducibility() -> None:
    """AC-12: Test identical config + version + seed produces identical scenarios."""
    generator1 = ScenarioGenerator()
    generator2 = ScenarioGenerator()

    seed = 2026

    scen_a = generator1.generate(seed, scenario_id="fixed_id_100")
    scen_b = generator2.generate(seed, scenario_id="fixed_id_100")

    # Complete structural and value equality
    assert scen_a == scen_b
    assert scen_a.observable_state == scen_b.observable_state
    assert scen_a.hidden_state == scen_b.hidden_state
    assert scen_a.model_dump() == scen_b.model_dump()


def test_multiple_independent_seeds() -> None:
    """AC-13: Test multiple seeds produce distinct, reproducible scenarios."""
    generator = ScenarioGenerator()
    seeds = [101, 202, 303, 404, 505]

    scenarios = [generator.generate(s) for s in seeds]

    # Confirm all have correct seed metadata
    for seed, scen in zip(seeds, scenarios, strict=True):
        assert scen.generation_seed == seed

    # Confirm scenarios across different seeds are distinct
    scenario_ids = [s.scenario_id for s in scenarios]
    assert len(set(scenario_ids)) == len(seeds)

    # Re-running each seed reproduces the exact scenario
    for seed, scen in zip(seeds, scenarios, strict=True):
        reproduced = generator.generate(seed, scenario_id=scen.scenario_id)
        assert reproduced == scen


def test_all_scenario_families_represented() -> None:
    """AC-05: Test all 8 scenario families are supported and can be generated."""
    generator = ScenarioGenerator()
    observed_families: set[ScenarioFamily] = set()

    # Generate across seeds to observe all families
    for seed in range(200):
        scen = generator.generate(seed)
        observed_families.add(scen.scenario_family)
        if len(observed_families) == len(ScenarioFamily):
            break

    assert observed_families == set(ScenarioFamily)


def test_all_recoverability_classes_represented() -> None:
    """AC-06: Test all 4 recoverability classes are supported and generated."""
    generator = ScenarioGenerator()
    observed_recoverabilities: set[RecoverabilityClass] = set()

    for seed in range(200):
        scen = generator.generate(seed)
        observed_recoverabilities.add(scen.hidden_state.recoverability)
        if len(observed_recoverabilities) == len(RecoverabilityClass):
            break

    assert observed_recoverabilities == set(RecoverabilityClass)


def test_all_customer_behavior_classes_represented() -> None:
    """AC-07: Test all 4 customer behavior classes are supported and generated."""
    generator = ScenarioGenerator()
    observed_behaviors: set[CustomerBehaviorClass] = set()

    for seed in range(200):
        scen = generator.generate(seed)
        observed_behaviors.add(scen.hidden_state.customer_behavior)
        if len(observed_behaviors) == len(CustomerBehaviorClass):
            break

    assert observed_behaviors == set(CustomerBehaviorClass)


def test_distribution_variation_across_dimensions() -> None:
    """AC-14: Test variation in amount, methods, temporal, historical, difficulty."""
    generator = ScenarioGenerator()

    methods: set[SimulatedPaymentMethod] = set()
    difficulties: set[ScenarioDifficulty] = set()
    amounts: list[int] = []
    hours: set[int] = set()

    for seed in range(100):
        scen = generator.generate(seed)
        methods.add(scen.observable_state.payment.method)
        difficulties.add(scen.hidden_state.scenario_difficulty)
        amounts.append(scen.observable_state.payment.amount)
        hours.add(scen.observable_state.temporal.hour_of_day)

    assert len(methods) >= 3
    assert len(difficulties) == 4
    assert min(amounts) >= 10000
    assert max(amounts) <= 5000000
    assert len(set(amounts)) > 20
    assert len(hours) > 10


def test_custom_configuration_application() -> None:
    """AC-15: Test custom versioned SimulationConfig governs scenario generation."""
    custom_config = SimulationConfig(
        configuration_version="custom-v2",
        scenario_version="scenario-v2",
        family_distribution={
            ScenarioFamily.TRANSIENT_FAILURE: 1.0,
            ScenarioFamily.BANK_SIDE_FAILURE: 0.0,
            ScenarioFamily.CUSTOMER_SIDE_FAILURE: 0.0,
            ScenarioFamily.AUTHENTICATION_FAILURE: 0.0,
            ScenarioFamily.PAYMENT_METHOD_FAILURE: 0.0,
            ScenarioFamily.GATEWAY_FAILURE: 0.0,
            ScenarioFamily.TIMEOUT: 0.0,
            ScenarioFamily.UNKNOWN_FAILURE: 0.0,
        },
    )

    generator = ScenarioGenerator(custom_config)
    scen = generator.generate(seed=777)

    assert scen.configuration_version == "custom-v2"
    assert scen.scenario_version == "scenario-v2"
    assert scen.scenario_family == ScenarioFamily.TRANSIENT_FAILURE
