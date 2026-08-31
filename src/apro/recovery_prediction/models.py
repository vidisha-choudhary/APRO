"""Data models, labels, and prediction schemas for APRO Phase 8 Recovery Prediction."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.recovery_prediction.enums import (
    OUTCOME_TAXONOMY_VERSION,
    RECOVERY_ACTION_ORDER,
    RECOVERY_ACTION_SCHEMA_VERSION,
    PredictedOutcomeState,
    PredictionUncertaintyState,
    RecoveryAction,
)


class RecoveryOutcomeLabel(BaseModel):
    """Ground-truth action-conditioned recovery outcome label."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    action: RecoveryAction
    outcome_state: PredictedOutcomeState
    recovered_amount: int = Field(ge=0)
    label_source: str = Field(default="governed_simulator_ground_truth")
    dataset_version: str
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    outcome_schema_version: str = Field(default=OUTCOME_TAXONOMY_VERSION)


class OutcomePrediction(BaseModel):
    """Model B outcome prediction for an observable context and action."""

    model_config = ConfigDict(frozen=True)

    prediction_id: str
    record_id: str
    scenario_id: str
    action: RecoveryAction
    model_name: str
    model_version: str
    dataset_version: str
    feature_schema_version: str
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    diagnosis_model_version: str | None = None
    predicted_success_probability: float = Field(ge=0.0, le=1.0)
    predicted_outcome_state: PredictedOutcomeState
    predicted_recovered_amount: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_state: PredictionUncertaintyState
    evaluation_run_id: str | None = None
    decision_latency_ms: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)


class MultiActionOutcomePrediction(BaseModel):
    """Container for outcome predictions across all candidate actions."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    record_id: str
    predictions: dict[RecoveryAction, OutcomePrediction]


class RecoveryOutcomeModelArtifact(BaseModel):
    """Portable, serializable trained Model B artifact with versioned provenance."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str
    algorithm: str
    feature_schema_version: str
    action_schema_version: str
    outcome_schema_version: str
    training_dataset_version: str
    training_seed: int
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    parameters: dict[str, Any]
    feature_names: list[str]
    diagnosis_model_version: str | None = None
    calibration_method: str | None = None
    calibration_parameters: dict[str, Any] = Field(default_factory=dict)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    action_order: list[RecoveryAction] = Field(
        default_factory=lambda: list(RECOVERY_ACTION_ORDER)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    deterministic_identity: str | None = None

    def compute_deterministic_identity(self) -> str:
        """Compute deterministic fingerprint of the model artifact."""
        identity_payload = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "feature_schema_version": self.feature_schema_version,
            "action_schema_version": self.action_schema_version,
            "outcome_schema_version": self.outcome_schema_version,
            "training_dataset_version": self.training_dataset_version,
            "training_seed": self.training_seed,
            "diagnosis_model_version": self.diagnosis_model_version,
            "parameters": self.parameters,
            "feature_names": self.feature_names,
            "calibration_method": self.calibration_method,
            "calibration_parameters": self.calibration_parameters,
            "hyperparameters": self.hyperparameters,
            "action_order": [a.value for a in self.action_order],
        }
        payload_json = json.dumps(identity_payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class RecoveryOutcomeExperimentConfig(BaseModel):
    """Declarative specification for Model B experiments."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str
    model_name: str
    model_version: str
    algorithm: str
    training_dataset_version: str
    feature_schema_version: str = Field(default="recovery-outcome-feature-v1")
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    outcome_schema_version: str = Field(default=OUTCOME_TAXONOMY_VERSION)
    training_seed: int = Field(default=42)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    calibration_method: str | None = None
    primary_selection_metric: str = Field(default="macro_f1")
    secondary_selection_metric: str = Field(default="log_loss")
    high_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    medium_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
