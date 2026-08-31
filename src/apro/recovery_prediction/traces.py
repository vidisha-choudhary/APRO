"""Prediction trace models for APRO Phase 8 Recovery Prediction."""

from pydantic import BaseModel, ConfigDict, Field

from apro.recovery_prediction.enums import (
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)


class RecoveryPredictionTrace(BaseModel):
    """Complete structured audit trace for an evaluated (context, action) prediction."""

    model_config = ConfigDict(frozen=True)

    prediction_id: str
    record_id: str
    scenario_id: str
    action: RecoveryAction
    dataset_version: str
    feature_schema_version: str
    action_schema_version: str
    diagnosis_model_version: str | None = None
    model_version: str
    predicted_success_probability: float = Field(ge=0.0, le=1.0)
    predicted_outcome_state: PredictedOutcomeState
    predicted_recovered_amount: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_state: PredictionUncertaintyState
    actual_outcome_state: PredictedOutcomeState
    actual_recovered_amount: int = Field(ge=0)
    is_correct_outcome: bool
    amount_error: int
    scenario_family: str
    payment_method: str
    payment_value_tier: str
    scenario_difficulty: str
    evaluation_run_id: str | None = None
    decision_latency_ms: float = 0.0
