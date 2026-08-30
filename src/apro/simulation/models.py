"""Domain models for synthetic simulation scenarios and outcomes."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.simulation.enums import (
    CustomerBehaviorClass,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
    SimulatedPaymentMethod,
)


class CustomerContext(BaseModel):
    """Observable pre-decision historical customer payment profile."""

    model_config = ConfigDict(frozen=True)

    customer_id: str
    previous_payment_count: int = Field(ge=0)
    previous_success_count: int = Field(ge=0)
    previous_failure_count: int = Field(ge=0)
    previous_recovery_count: int = Field(ge=0)
    previous_retry_success: int = Field(ge=0)
    previous_payment_link_success: int = Field(ge=0)


class PaymentContext(BaseModel):
    """Observable payment opportunity attributes."""

    model_config = ConfigDict(frozen=True)

    payment_id: str
    amount: int = Field(gt=0, description="Amount in minor units (paise)")
    currency: str = "INR"
    method: SimulatedPaymentMethod
    attempt_count: int = Field(ge=1)


class FailureContext(BaseModel):
    """Observable failure error codes and message descriptions."""

    model_config = ConfigDict(frozen=True)

    failure_reason: str
    failure_code: str
    decline_code: str | None = None


class TemporalContext(BaseModel):
    """Observable timing and historical temporal proximity context."""

    model_config = ConfigDict(frozen=True)

    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    is_weekend: bool
    time_since_previous_attempt_seconds: int | None = Field(default=None, ge=0)
    time_since_previous_successful_payment_seconds: int | None = Field(
        default=None, ge=0
    )


class ObservableScenarioState(BaseModel):
    """APRO-facing observable scenario representation available at decision time."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    customer: CustomerContext
    payment: PaymentContext
    failure: FailureContext
    temporal: TemporalContext
    candidate_actions: list[SimulatedActionType]


class HiddenScenarioState(BaseModel):
    """Ground-truth simulation state strictly isolated from APRO consumers."""

    model_config = ConfigDict(frozen=True)

    true_failure_mechanism: str
    recoverability: RecoverabilityClass
    customer_behavior: CustomerBehaviorClass
    latent_customer_intent: float = Field(ge=0.0, le=1.0)
    latent_bank_condition: float = Field(ge=0.0, le=1.0)
    scenario_difficulty: ScenarioDifficulty
    true_action_probabilities: dict[SimulatedActionType, float]
    potential_outcomes: dict[SimulatedActionType, SimulatedOutcomeStatus]


class SimulationScenario(BaseModel):
    """Full synthetic recovery scenario with metadata, observable, and hidden state."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    generation_seed: int
    scenario_version: str
    configuration_version: str
    scenario_family: ScenarioFamily
    observable_state: ObservableScenarioState
    hidden_state: HiddenScenarioState

    def to_observable_projection(self) -> ObservableScenarioState:
        """Project scenario into pure APRO-facing observable state without leakage."""
        return self.observable_state


class SimulatedActionOutcome(BaseModel):
    """Result of executing an action within a synthetic scenario."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    action: SimulatedActionType
    status: SimulatedOutcomeStatus
    recovered_amount: int = Field(ge=0)
    attempt_duration_seconds: int = Field(ge=0)
    failure_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
