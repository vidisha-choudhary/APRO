"""Structured evaluation traces for APRO Phase 9 Decision Engine."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.decision.enums import (
    DECISION_MODEL_SCHEMA_VERSION,
    ECONOMIC_CONFIG_SCHEMA_VERSION,
    POLICY_CONFIG_SCHEMA_VERSION,
    RECOVERY_ACTION_SCHEMA_VERSION,
    DecisionStatus,
    RecoveryAction,
)
from apro.decision.models import ActionEligibility, ActionUtility


class RecoveryDecisionTrace(BaseModel):
    """Structured decision trace recording decision and oracle comparison."""

    model_config = ConfigDict(frozen=True)

    # Core Decision Identity & Context
    decision_id: str
    record_id: str
    scenario_id: str
    recovery_case_id: str | None = None
    selected_action: RecoveryAction | None
    decision_status: DecisionStatus
    utility_by_action: dict[RecoveryAction, ActionUtility]
    eligibility_by_action: dict[RecoveryAction, ActionEligibility]
    expected_recovery_value: int | None
    expected_gross_recovery: int | None
    expected_cost: int | None
    decision_confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    decision_latency_ms: float = Field(ge=0.0)

    # Version & Provenance Metadata
    diagnosis_model_version: str
    outcome_model_version: str
    policy_version: str = Field(default=POLICY_CONFIG_SCHEMA_VERSION)
    economic_config_version: str = Field(default=ECONOMIC_CONFIG_SCHEMA_VERSION)
    decision_model_version: str = Field(default=DECISION_MODEL_SCHEMA_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    feature_schema_version: str = Field(default="feature-schema-v1")
    dataset_version: str
    evaluation_run_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Evaluator-Side Potential Outcome Comparison (Simulator Ground Truth)
    oracle_best_action: RecoveryAction
    oracle_best_value: int = Field(ge=0)
    realized_value_under_selected: int = Field(ge=0)
    decision_regret: int = Field(ge=0)
    oracle_gap: int = Field(ge=0)
    is_oracle_match: bool
    is_unnecessary_intervention: bool
    is_ineligible_selection: bool = False
    is_constraint_violation: bool = False

    # Slice Dimensions
    scenario_family: str
    payment_method: str
    payment_value_tier: str
    scenario_difficulty: str
    failure_diagnosis: str
    diagnosis_confidence_tier: str
    seed: int
    historical_failure_count: int
    metadata_completeness: float
