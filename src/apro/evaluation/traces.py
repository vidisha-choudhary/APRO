"""Per-case benchmark evaluation trace schema for APRO Phase 6."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.simulation.enums import (
    CustomerBehaviorClass,
    PaymentValueTier,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
)


class CaseEvaluationTrace(BaseModel):
    """Immutable audit and evaluation trace for a single strategy-case decision."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    scenario_id: str
    strategy_name: str
    strategy_version: str
    dataset_version: str
    scenario_version: str
    configuration_version: str
    seed: int

    payment_amount: int = Field(
        ge=0, description="Payment amount in integer minor units"
    )
    candidate_actions: list[SimulatedActionType]
    chosen_action: SimulatedActionType
    outcome_status: SimulatedOutcomeStatus
    recovered_amount: int = Field(
        ge=0, description="Amount recovered in integer minor units"
    )
    attempt_duration_seconds: int = Field(ge=0)

    # Counterfactual / Ground Truth Analysis
    best_achievable_action: SimulatedActionType
    best_achievable_value: int = Field(ge=0)
    regret: int = Field(ge=0, description="best_achievable_value - recovered_amount")
    is_optimal: bool
    is_intervention: bool = Field(description="True if chosen_action is not STOP")
    is_unnecessary_intervention: bool = Field(
        description="True if intervention attempted on non-recoverable case"
    )
    decision_latency_ms: float = Field(ge=0.0)

    # Dimensional Context for Subgroup Aggregation
    scenario_family: ScenarioFamily
    recoverability: RecoverabilityClass
    customer_behavior: CustomerBehaviorClass
    scenario_difficulty: ScenarioDifficulty
    payment_value_tier: PaymentValueTier

    metadata: dict[str, Any] = Field(default_factory=dict)
