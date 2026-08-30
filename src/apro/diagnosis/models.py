import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.diagnosis.enums import (
    DIAGNOSIS_TAXONOMY_ORDER,
    DIAGNOSIS_TAXONOMY_VERSION,
    DiagnosisCategory,
    UncertaintyState,
)


class DiagnosisLabel(BaseModel):
    """Ground truth diagnosis label constructed from EvaluationTruthRecord."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    failure_category: DiagnosisCategory
    taxonomy_version: str = Field(default=DIAGNOSIS_TAXONOMY_VERSION)
    label_source: str = Field(default="governed_simulator_ground_truth")


class DiagnosisResult(BaseModel):
    """Model A diagnosis prediction result for an observable payment failure."""

    model_config = ConfigDict(frozen=True)

    prediction_id: str
    record_id: str
    scenario_id: str
    model_name: str
    model_version: str
    dataset_version: str
    feature_schema_version: str
    taxonomy_version: str = Field(default=DIAGNOSIS_TAXONOMY_VERSION)
    predicted_category: DiagnosisCategory
    class_probabilities: dict[DiagnosisCategory, float]
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_state: UncertaintyState
    decision_latency_ms: float = 0.0

    def validate_probabilities(self) -> None:
        """Validate probability distribution constraints across the full taxonomy."""
        for cat in DIAGNOSIS_TAXONOMY_ORDER:
            if cat not in self.class_probabilities:
                msg = f"Missing probability for taxonomy class {cat.value}."
                raise ValueError(msg)
            p = self.class_probabilities[cat]
            if p < 0.0 or p > 1.0:
                msg = f"Probability for {cat.value} ({p}) is outside [0, 1]."
                raise ValueError(msg)
        total_p = sum(self.class_probabilities.values())
        if abs(total_p - 1.0) > 1e-4:
            msg = f"Probabilities must sum to ~1.0 (got {total_p:.6f})."
            raise ValueError(msg)


class DiagnosisModelArtifact(BaseModel):
    """Portable, serializable trained model artifact with versioned provenance."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str
    algorithm: str
    feature_schema_version: str
    taxonomy_version: str
    training_dataset_version: str
    training_seed: int
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    parameters: dict[str, Any]
    feature_names: list[str]
    calibration_method: str | None = None
    calibration_parameters: dict[str, Any] = Field(default_factory=dict)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    class_order: list[DiagnosisCategory] = Field(
        default_factory=lambda: list(DIAGNOSIS_TAXONOMY_ORDER)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    deterministic_identity: str | None = None

    def compute_deterministic_identity(self) -> str:
        """Compute deterministic fingerprint of the model excluding creation time."""
        identity_payload = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "feature_schema_version": self.feature_schema_version,
            "taxonomy_version": self.taxonomy_version,
            "training_dataset_version": self.training_dataset_version,
            "training_seed": self.training_seed,
            "parameters": self.parameters,
            "feature_names": self.feature_names,
            "calibration_method": self.calibration_method,
            "calibration_parameters": self.calibration_parameters,
            "hyperparameters": self.hyperparameters,
            "class_order": [c.value for c in self.class_order],
        }
        payload_json = json.dumps(identity_payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class DiagnosisExperimentConfig(BaseModel):
    """Declarative specification for Model A training and evaluation experiments."""

    model_config = ConfigDict(frozen=True)

    experiment_id: str
    model_name: str
    model_version: str
    algorithm: str
    training_dataset_version: str
    feature_schema_version: str = Field(default="diagnosis-feature-v1")
    taxonomy_version: str = Field(default=DIAGNOSIS_TAXONOMY_VERSION)
    training_seed: int = Field(default=42)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    calibration_method: str | None = None
    primary_selection_metric: str = Field(default="macro_f1")
    secondary_selection_metric: str = Field(default="log_loss")
    high_confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    medium_confidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
