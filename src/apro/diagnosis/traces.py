"""Diagnosis prediction trace data structures for APRO Phase 7."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
    UncertaintyState,
)
from apro.simulation.enums import (
    PaymentValueTier,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedPaymentMethod,
)


class DiagnosisPredictionTrace(BaseModel):
    """Per-case diagnosis prediction trace with optional evaluation metadata."""

    model_config = ConfigDict(frozen=True)

    prediction_id: str
    record_id: str
    scenario_id: str
    dataset_version: str
    feature_schema_version: str
    taxonomy_version: str = Field(default=DIAGNOSIS_TAXONOMY_VERSION)
    model_name: str
    model_version: str
    predicted_category: DiagnosisCategory
    class_probabilities: dict[DiagnosisCategory, float]
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_state: UncertaintyState
    actual_category: DiagnosisCategory | None = Field(
        default=None, description="Evaluator-side ground truth only"
    )
    is_correct: bool | None = Field(default=None)
    decision_latency_ms: float = Field(default=0.0, ge=0.0)
    scenario_family: ScenarioFamily
    payment_value_tier: PaymentValueTier
    payment_method: SimulatedPaymentMethod
    scenario_difficulty: ScenarioDifficulty
    seed: int
    metadata: dict[str, Any] = Field(default_factory=dict)
