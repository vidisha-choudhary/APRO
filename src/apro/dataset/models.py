"""Dataset data models and schema definitions for APRO Phase 6."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.dataset.enums import DatasetType
from apro.simulation.enums import (
    CustomerBehaviorClass,
    RecoverabilityClass,
    ScenarioDifficulty,
    ScenarioFamily,
    SimulatedActionType,
    SimulatedOutcomeStatus,
    SimulatedPaymentMethod,
)


class FeatureSnapshot(BaseModel):
    """Decision-time immutable feature snapshot."""

    model_config = ConfigDict(frozen=True)

    feature_schema_version: str = Field(default="feature-schema-v1", min_length=1)
    decision_timestamp: str = Field(
        description="ISO 8601 timestamp of the decision point"
    )

    # Observable Payment Context
    payment_id: str
    payment_amount: int = Field(
        gt=0, description="Amount in integer minor units (e.g. paise)"
    )
    currency: str = Field(default="INR")
    payment_method: SimulatedPaymentMethod
    attempt_count: int = Field(ge=1)

    # Observable Failure Context
    failure_reason: str
    failure_code: str
    decline_code: str | None = None

    # Observable Customer History Context
    customer_id: str
    previous_payment_count: int = Field(ge=0)
    previous_success_count: int = Field(ge=0)
    previous_failure_count: int = Field(ge=0)
    previous_recovery_count: int = Field(ge=0)
    previous_retry_success: int = Field(ge=0)
    previous_payment_link_success: int = Field(ge=0)

    # Observable Temporal Context
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    is_weekend: bool
    time_since_previous_attempt_seconds: int | None = Field(default=None, ge=0)
    time_since_previous_successful_payment_seconds: int | None = None

    # Candidate Actions available at decision time
    candidate_actions: list[SimulatedActionType] = Field(min_length=1)


class TrainingObservation(BaseModel):
    """Historical observable action and outcome for training without simulator truth."""

    model_config = ConfigDict(frozen=True)

    observed_action: SimulatedActionType
    observed_outcome_status: SimulatedOutcomeStatus
    recovered_amount: int = Field(ge=0)


class ModelInputRecord(BaseModel):
    """Governed model-facing record allowed at decision time."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    dataset_type: DatasetType
    dataset_version: str
    scenario_id: str
    generation_seed: int
    scenario_version: str
    configuration_version: str
    feature_schema_version: str
    benchmark_version: str | None = None
    features: FeatureSnapshot
    training_label: TrainingObservation | None = None


class EvaluationTruthRecord(BaseModel):
    """Simulator-only ground truth record for evaluation and counterfactuals."""

    model_config = ConfigDict(frozen=True)

    record_id: str
    scenario_id: str
    scenario_family: ScenarioFamily
    recoverability: RecoverabilityClass
    customer_behavior: CustomerBehaviorClass
    true_failure_mechanism: str
    latent_customer_intent: float
    latent_bank_condition: float
    scenario_difficulty: ScenarioDifficulty
    true_action_probabilities: dict[SimulatedActionType, float]
    potential_outcomes: dict[SimulatedActionType, SimulatedOutcomeStatus]
    best_achievable_action: SimulatedActionType
    best_achievable_value: int = Field(ge=0)


class DatasetRecord(BaseModel):
    """Combined governed record pairing model input with evaluation truth."""

    model_config = ConfigDict(frozen=True)

    model_input: ModelInputRecord
    evaluation_truth: EvaluationTruthRecord


class DatasetManifest(BaseModel):
    """Machine-readable provenance manifest for a governed dataset."""

    model_config = ConfigDict(frozen=True)

    dataset_version: str
    dataset_type: DatasetType
    scenario_version: str
    configuration_version: str
    feature_schema_version: str
    benchmark_version: str | None = None
    seed_list: list[int]
    record_count: int = Field(ge=0)
    split_policy: str | None = None
    temporal_cutoff: str | None = None
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernedDataset(BaseModel):
    """Collection of dataset records governed by an immutable manifest."""

    model_config = ConfigDict(frozen=True)

    manifest: DatasetManifest
    records: tuple[DatasetRecord, ...] = Field(default_factory=tuple)

    def get_model_inputs(self) -> list[ModelInputRecord]:
        """Return model-facing records strictly isolated from ground truth."""
        return [r.model_input for r in self.records]

    def get_evaluation_truths(self) -> list[EvaluationTruthRecord]:
        """Return simulator-only evaluation truth records."""
        return [r.evaluation_truth for r in self.records]

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> DatasetRecord:
        return self.records[index]
