"""Unit tests for SimulationConfig validation rules (Phase 5)."""

import pytest

from apro.simulation.config import SimulationConfig
from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def test_valid_default_configuration() -> None:
    """AC-15: Test default SimulationConfig passes all validations."""
    config = SimulationConfig()
    assert config.configuration_version == "config-v1"
    assert config.scenario_version == "scenario-v1"
    assert len(config.family_distribution) == len(ScenarioFamily)
    assert len(config.recoverability_distribution) == len(RecoverabilityClass)
    assert len(config.behavior_distribution) == len(CustomerBehaviorClass)
    assert len(config.value_tier_distribution) == len(PaymentValueTier)
    assert len(config.method_distribution) == len(SimulatedPaymentMethod)
    assert len(config.difficulty_distribution) == len(ScenarioDifficulty)


def test_distribution_sum_not_one_raises_error() -> None:
    """AC-16: Test probability distribution not summing to 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="probabilities must sum to 1.0"):
        SimulationConfig(
            family_distribution={
                ScenarioFamily.TRANSIENT_FAILURE: 0.5,
                ScenarioFamily.BANK_SIDE_FAILURE: 0.1,
                ScenarioFamily.CUSTOMER_SIDE_FAILURE: 0.1,
                ScenarioFamily.AUTHENTICATION_FAILURE: 0.1,
                ScenarioFamily.PAYMENT_METHOD_FAILURE: 0.1,
                ScenarioFamily.GATEWAY_FAILURE: 0.1,
                ScenarioFamily.TIMEOUT: 0.1,
                ScenarioFamily.UNKNOWN_FAILURE: 0.1,  # Sum = 1.2
            }
        )


def test_negative_probability_raises_error() -> None:
    """AC-16: Test negative probability in distribution raises ValueError."""
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        SimulationConfig(
            recoverability_distribution={
                RecoverabilityClass.HIGHLY_RECOVERABLE: 1.1,
                RecoverabilityClass.MODERATELY_RECOVERABLE: -0.1,
                RecoverabilityClass.LOW_RECOVERABILITY: 0.0,
                RecoverabilityClass.NON_RECOVERABLE: 0.0,
            }
        )


def test_empty_distribution_raises_error() -> None:
    """AC-16: Test empty distribution raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        SimulationConfig(behavior_distribution={})


def test_missing_distribution_keys_raises_error() -> None:
    """AC-16: Test distribution missing required enum keys raises ValueError."""
    with pytest.raises(ValueError, match="missing required keys"):
        SimulationConfig(
            method_distribution={
                SimulatedPaymentMethod.UPI: 0.6,
                SimulatedPaymentMethod.CARD: 0.4,
                # Missing NETBANKING, WALLET, OTHER_SUPPORTED_METHOD
            }
        )


def test_invalid_amount_range_raises_error() -> None:
    """AC-16: Test min > max or min <= 0 in amount_ranges raises ValueError."""
    with pytest.raises(ValueError, match="min .* > max"):
        SimulationConfig(
            amount_ranges={
                PaymentValueTier.LOW_VALUE: (50000, 10000),  # min > max
                PaymentValueTier.MEDIUM_VALUE: (100000, 1000000),
                PaymentValueTier.HIGH_VALUE: (1000000, 5000000),
            }
        )

    with pytest.raises(ValueError, match="must be > 0"):
        SimulationConfig(
            amount_ranges={
                PaymentValueTier.LOW_VALUE: (0, 10000),  # min <= 0
                PaymentValueTier.MEDIUM_VALUE: (100000, 1000000),
                PaymentValueTier.HIGH_VALUE: (1000000, 5000000),
            }
        )


def test_missing_base_action_effectiveness_raises_error() -> None:
    """AC-16: Test missing recoverability class in base action raises ValueError."""
    with pytest.raises(ValueError, match="Missing base action effectiveness"):
        SimulationConfig(
            base_action_effectiveness={
                RecoverabilityClass.HIGHLY_RECOVERABLE: {
                    SimulatedActionType.RETRY: 0.8,
                    SimulatedActionType.PAYMENT_LINK: 0.8,
                    SimulatedActionType.OUTREACH: 0.8,
                    SimulatedActionType.STOP: 0.0,
                    SimulatedActionType.ESCALATE: 0.1,
                }
                # Missing other classes
            }
        )


def test_missing_family_modifier_keys_raises_error() -> None:
    """AC-16 (Correction B): Test missing family modifiers raises ValueError."""
    with pytest.raises(ValueError, match="Missing family action modifiers"):
        SimulationConfig(
            family_action_modifiers={
                ScenarioFamily.TRANSIENT_FAILURE: {
                    SimulatedActionType.RETRY: 0.1,
                    SimulatedActionType.PAYMENT_LINK: 0.0,
                    SimulatedActionType.OUTREACH: 0.0,
                    SimulatedActionType.STOP: 0.0,
                    SimulatedActionType.ESCALATE: 0.0,
                }
                # Missing other families
            }
        )

    default_modifiers = SimulationConfig().family_action_modifiers.copy()
    # Incomplete actions for one family
    default_modifiers[ScenarioFamily.TRANSIENT_FAILURE] = {
        SimulatedActionType.RETRY: 0.1
    }
    with pytest.raises(ValueError, match="Missing modifier for action"):
        SimulationConfig(family_action_modifiers=default_modifiers)


def test_missing_behavior_modifier_keys_raises_error() -> None:
    """AC-16 (Correction B): Test missing behavior modifiers raises ValueError."""
    with pytest.raises(ValueError, match="Missing behavior action modifiers"):
        SimulationConfig(
            behavior_action_modifiers={
                CustomerBehaviorClass.NORMAL: {
                    SimulatedActionType.RETRY: 0.0,
                    SimulatedActionType.PAYMENT_LINK: 0.0,
                    SimulatedActionType.OUTREACH: 0.0,
                    SimulatedActionType.STOP: 0.0,
                    SimulatedActionType.ESCALATE: 0.0,
                }
            }
        )


def test_out_of_range_modifier_values_raises_error() -> None:
    """AC-16 (Correction B): Test modifier values outside [-1.0, 1.0] raise error."""
    default_modifiers = SimulationConfig().family_action_modifiers.copy()
    default_modifiers[ScenarioFamily.TRANSIENT_FAILURE] = {
        SimulatedActionType.RETRY: 1.5,  # > 1.0
        SimulatedActionType.PAYMENT_LINK: 0.0,
        SimulatedActionType.OUTREACH: 0.0,
        SimulatedActionType.STOP: 0.0,
        SimulatedActionType.ESCALATE: 0.0,
    }
    with pytest.raises(ValueError, match="must be between -1.0 and 1.0"):
        SimulationConfig(family_action_modifiers=default_modifiers)


def test_invalid_difficulty_noise_raises_error() -> None:
    """AC-16 (Correction B): Test invalid difficulty noise raises ValueError."""
    with pytest.raises(ValueError, match="Missing difficulty noise"):
        SimulationConfig(
            difficulty_noise={
                ScenarioDifficulty.EASY: 0.05
            }  # Missing other difficulties
        )

    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        SimulationConfig(
            difficulty_noise={
                ScenarioDifficulty.EASY: -0.1,  # Negative
                ScenarioDifficulty.AMBIGUOUS: 0.1,
                ScenarioDifficulty.HARD: 0.2,
                ScenarioDifficulty.ADVERSARIAL: 0.3,
            }
        )
