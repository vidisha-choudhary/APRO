"""Simulation configuration models and validation for APRO Phase 5."""

import math
from collections.abc import Iterable, Mapping
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedPaymentMethod,
)


def _validate_distribution(
    dist: Mapping[Any, float],
    name: str,
    expected_keys: Iterable[Any] | None = None,
) -> None:
    """Validate that a probability distribution is non-negative and sums to 1.0."""
    if not dist:
        msg = f"Distribution '{name}' cannot be empty."
        raise ValueError(msg)

    total = sum(dist.values())
    if not math.isclose(total, 1.0, abs_tol=1e-5):
        msg = f"Distribution '{name}' probabilities must sum to 1.0 (got {total:.6f})."
        raise ValueError(msg)

    for k, v in dist.items():
        if v < 0.0 or v > 1.0:
            msg = (
                f"Probability for '{k}' in '{name}' must be between 0.0 and 1.0 "
                f"(got {v})."
            )
            raise ValueError(msg)

    if expected_keys is not None:
        missing = [key for key in expected_keys if key not in dist]
        if missing:
            msg = f"Distribution '{name}' is missing required keys: {missing}."
            raise ValueError(msg)


class SimulationConfig(BaseModel):
    """Immutable versioned configuration governing synthetic scenario generation."""

    model_config = ConfigDict(frozen=True)

    configuration_version: str = Field(default="config-v1", min_length=1)
    scenario_version: str = Field(default="scenario-v1", min_length=1)

    family_distribution: dict[ScenarioFamily, float] = Field(
        default_factory=lambda: {
            ScenarioFamily.TRANSIENT_FAILURE: 0.20,
            ScenarioFamily.BANK_SIDE_FAILURE: 0.15,
            ScenarioFamily.CUSTOMER_SIDE_FAILURE: 0.15,
            ScenarioFamily.AUTHENTICATION_FAILURE: 0.15,
            ScenarioFamily.PAYMENT_METHOD_FAILURE: 0.10,
            ScenarioFamily.GATEWAY_FAILURE: 0.10,
            ScenarioFamily.TIMEOUT: 0.10,
            ScenarioFamily.UNKNOWN_FAILURE: 0.05,
        }
    )

    recoverability_distribution: dict[RecoverabilityClass, float] = Field(
        default_factory=lambda: {
            RecoverabilityClass.HIGHLY_RECOVERABLE: 0.30,
            RecoverabilityClass.MODERATELY_RECOVERABLE: 0.35,
            RecoverabilityClass.LOW_RECOVERABILITY: 0.20,
            RecoverabilityClass.NON_RECOVERABLE: 0.15,
        }
    )

    behavior_distribution: dict[CustomerBehaviorClass, float] = Field(
        default_factory=lambda: {
            CustomerBehaviorClass.HIGHLY_RESPONSIVE: 0.25,
            CustomerBehaviorClass.NORMAL: 0.45,
            CustomerBehaviorClass.LOW_RESPONSIVENESS: 0.20,
            CustomerBehaviorClass.UNPREDICTABLE: 0.10,
        }
    )

    value_tier_distribution: dict[PaymentValueTier, float] = Field(
        default_factory=lambda: {
            PaymentValueTier.LOW_VALUE: 0.50,
            PaymentValueTier.MEDIUM_VALUE: 0.35,
            PaymentValueTier.HIGH_VALUE: 0.15,
        }
    )

    method_distribution: dict[SimulatedPaymentMethod, float] = Field(
        default_factory=lambda: {
            SimulatedPaymentMethod.UPI: 0.45,
            SimulatedPaymentMethod.CARD: 0.30,
            SimulatedPaymentMethod.NETBANKING: 0.15,
            SimulatedPaymentMethod.WALLET: 0.08,
            SimulatedPaymentMethod.OTHER_SUPPORTED_METHOD: 0.02,
        }
    )

    difficulty_distribution: dict[ScenarioDifficulty, float] = Field(
        default_factory=lambda: {
            ScenarioDifficulty.EASY: 0.40,
            ScenarioDifficulty.AMBIGUOUS: 0.30,
            ScenarioDifficulty.HARD: 0.20,
            ScenarioDifficulty.ADVERSARIAL: 0.10,
        }
    )

    amount_ranges: dict[PaymentValueTier, tuple[int, int]] = Field(
        default_factory=lambda: {
            PaymentValueTier.LOW_VALUE: (10000, 100000),  # 100 to 1,000 INR
            PaymentValueTier.MEDIUM_VALUE: (100000, 1000000),  # 1,000 to 10,000 INR
            PaymentValueTier.HIGH_VALUE: (1000000, 5000000),  # 10,000 to 50,000 INR
        }
    )

    base_action_effectiveness: dict[
        RecoverabilityClass, dict[SimulatedActionType, float]
    ] = Field(
        default_factory=lambda: {
            RecoverabilityClass.HIGHLY_RECOVERABLE: {
                SimulatedActionType.RETRY: 0.85,
                SimulatedActionType.PAYMENT_LINK: 0.80,
                SimulatedActionType.OUTREACH: 0.75,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.10,
            },
            RecoverabilityClass.MODERATELY_RECOVERABLE: {
                SimulatedActionType.RETRY: 0.50,
                SimulatedActionType.PAYMENT_LINK: 0.55,
                SimulatedActionType.OUTREACH: 0.45,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.20,
            },
            RecoverabilityClass.LOW_RECOVERABILITY: {
                SimulatedActionType.RETRY: 0.20,
                SimulatedActionType.PAYMENT_LINK: 0.25,
                SimulatedActionType.OUTREACH: 0.20,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.30,
            },
            RecoverabilityClass.NON_RECOVERABLE: {
                SimulatedActionType.RETRY: 0.00,
                SimulatedActionType.PAYMENT_LINK: 0.00,
                SimulatedActionType.OUTREACH: 0.00,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.00,
            },
        }
    )

    family_action_modifiers: dict[ScenarioFamily, dict[SimulatedActionType, float]] = (
        Field(
            default_factory=lambda: {
                ScenarioFamily.TRANSIENT_FAILURE: {
                    SimulatedActionType.RETRY: 0.15,
                    SimulatedActionType.PAYMENT_LINK: 0.00,
                    SimulatedActionType.OUTREACH: -0.05,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.BANK_SIDE_FAILURE: {
                    SimulatedActionType.RETRY: -0.10,
                    SimulatedActionType.PAYMENT_LINK: 0.10,
                    SimulatedActionType.OUTREACH: 0.05,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.05,
                },
                ScenarioFamily.CUSTOMER_SIDE_FAILURE: {
                    SimulatedActionType.RETRY: -0.20,
                    SimulatedActionType.PAYMENT_LINK: 0.15,
                    SimulatedActionType.OUTREACH: 0.20,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.AUTHENTICATION_FAILURE: {
                    SimulatedActionType.RETRY: -0.15,
                    SimulatedActionType.PAYMENT_LINK: 0.15,
                    SimulatedActionType.OUTREACH: 0.10,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.PAYMENT_METHOD_FAILURE: {
                    SimulatedActionType.RETRY: -0.25,
                    SimulatedActionType.PAYMENT_LINK: 0.20,
                    SimulatedActionType.OUTREACH: 0.10,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.GATEWAY_FAILURE: {
                    SimulatedActionType.RETRY: 0.10,
                    SimulatedActionType.PAYMENT_LINK: 0.05,
                    SimulatedActionType.OUTREACH: -0.05,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.TIMEOUT: {
                    SimulatedActionType.RETRY: 0.10,
                    SimulatedActionType.PAYMENT_LINK: 0.00,
                    SimulatedActionType.OUTREACH: -0.05,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
                ScenarioFamily.UNKNOWN_FAILURE: {
                    SimulatedActionType.RETRY: 0.00,
                    SimulatedActionType.PAYMENT_LINK: 0.00,
                    SimulatedActionType.OUTREACH: 0.00,
                    SimulatedActionType.STOP: 0.00,
                    SimulatedActionType.ESCALATE: 0.00,
                },
            }
        )
    )

    behavior_action_modifiers: dict[
        CustomerBehaviorClass, dict[SimulatedActionType, float]
    ] = Field(
        default_factory=lambda: {
            CustomerBehaviorClass.HIGHLY_RESPONSIVE: {
                SimulatedActionType.RETRY: 0.05,
                SimulatedActionType.PAYMENT_LINK: 0.20,
                SimulatedActionType.OUTREACH: 0.25,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.00,
            },
            CustomerBehaviorClass.NORMAL: {
                SimulatedActionType.RETRY: 0.00,
                SimulatedActionType.PAYMENT_LINK: 0.00,
                SimulatedActionType.OUTREACH: 0.00,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.00,
            },
            CustomerBehaviorClass.LOW_RESPONSIVENESS: {
                SimulatedActionType.RETRY: 0.00,
                SimulatedActionType.PAYMENT_LINK: -0.15,
                SimulatedActionType.OUTREACH: -0.20,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.00,
            },
            CustomerBehaviorClass.UNPREDICTABLE: {
                SimulatedActionType.RETRY: -0.05,
                SimulatedActionType.PAYMENT_LINK: -0.05,
                SimulatedActionType.OUTREACH: -0.05,
                SimulatedActionType.STOP: 0.00,
                SimulatedActionType.ESCALATE: 0.05,
            },
        }
    )

    difficulty_noise: dict[ScenarioDifficulty, float] = Field(
        default_factory=lambda: {
            ScenarioDifficulty.EASY: 0.02,
            ScenarioDifficulty.AMBIGUOUS: 0.08,
            ScenarioDifficulty.HARD: 0.15,
            ScenarioDifficulty.ADVERSARIAL: 0.25,
        }
    )

    @model_validator(mode="after")
    def validate_all(self) -> Self:
        """Validate all distributions and parameter bounds."""
        _validate_distribution(
            self.family_distribution, "family_distribution", list(ScenarioFamily)
        )
        _validate_distribution(
            self.recoverability_distribution,
            "recoverability_distribution",
            list(RecoverabilityClass),
        )
        _validate_distribution(
            self.behavior_distribution,
            "behavior_distribution",
            list(CustomerBehaviorClass),
        )
        _validate_distribution(
            self.value_tier_distribution,
            "value_tier_distribution",
            list(PaymentValueTier),
        )
        _validate_distribution(
            self.method_distribution,
            "method_distribution",
            list(SimulatedPaymentMethod),
        )
        _validate_distribution(
            self.difficulty_distribution,
            "difficulty_distribution",
            list(ScenarioDifficulty),
        )

        for tier in PaymentValueTier:
            if tier not in self.amount_ranges:
                msg = f"Missing amount range for tier '{tier}'."
                raise ValueError(msg)
            min_amt, max_amt = self.amount_ranges[tier]
            if min_amt <= 0:
                msg = f"Minimum amount for '{tier}' must be > 0 (got {min_amt})."
                raise ValueError(msg)
            if min_amt > max_amt:
                msg = (
                    f"Invalid amount range for '{tier}': "
                    f"min ({min_amt}) > max ({max_amt})."
                )
                raise ValueError(msg)

        for rec in RecoverabilityClass:
            if rec not in self.base_action_effectiveness:
                msg = f"Missing base action effectiveness for recoverability '{rec}'."
                raise ValueError(msg)
            for act in SimulatedActionType:
                if act not in self.base_action_effectiveness[rec]:
                    msg = (
                        f"Missing base effectiveness for action '{act}' in "
                        f"recoverability '{rec}'."
                    )
                    raise ValueError(msg)
                prob = self.base_action_effectiveness[rec][act]
                if prob < 0.0 or prob > 1.0:
                    msg = (
                        f"Base probability for '{rec}/{act}' must be between "
                        f"0.0 and 1.0 (got {prob})."
                    )
                    raise ValueError(msg)

        # Validate family_action_modifiers (Correction B)
        for family in ScenarioFamily:
            if family not in self.family_action_modifiers:
                msg = f"Missing family action modifiers for family '{family}'."
                raise ValueError(msg)
            for act in SimulatedActionType:
                if act not in self.family_action_modifiers[family]:
                    msg = f"Missing modifier for action '{act}' in family '{family}'."
                    raise ValueError(msg)
                mod = self.family_action_modifiers[family][act]
                if mod < -1.0 or mod > 1.0:
                    msg = (
                        f"Family action modifier for '{family}/{act}' must be "
                        f"between -1.0 and 1.0 (got {mod})."
                    )
                    raise ValueError(msg)

        # Validate behavior_action_modifiers (Correction B)
        for behavior in CustomerBehaviorClass:
            if behavior not in self.behavior_action_modifiers:
                msg = f"Missing behavior action modifiers for behavior '{behavior}'."
                raise ValueError(msg)
            for act in SimulatedActionType:
                if act not in self.behavior_action_modifiers[behavior]:
                    msg = (
                        f"Missing modifier for action '{act}' in behavior '{behavior}'."
                    )
                    raise ValueError(msg)
                mod = self.behavior_action_modifiers[behavior][act]
                if mod < -1.0 or mod > 1.0:
                    msg = (
                        f"Behavior action modifier for '{behavior}/{act}' must be "
                        f"between -1.0 and 1.0 (got {mod})."
                    )
                    raise ValueError(msg)

        # Validate difficulty_noise (Correction B)
        for diff in ScenarioDifficulty:
            if diff not in self.difficulty_noise:
                msg = f"Missing difficulty noise for difficulty '{diff}'."
                raise ValueError(msg)
            noise = self.difficulty_noise[diff]
            if noise < 0.0 or noise > 1.0:
                msg = (
                    f"Difficulty noise for '{diff}' must be between 0.0 and 1.0 "
                    f"(got {noise})."
                )
                raise ValueError(msg)

        return self
