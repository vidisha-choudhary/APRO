"""Auditable policy evaluation trace generation without simulator leakage."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from apro.policy.enums import (
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_TRACE_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_SCHEMA_VERSION,
    RecoveryAction,
)


class PolicyEvaluationTrace(BaseModel):
    """Complete, sanitized step-by-step trace of policy evaluation."""

    model_config = ConfigDict(frozen=True)

    policy_decision_id: str
    case_id: str
    payment_id: str
    event_id: str | None = None
    decision_id: str | None = None
    requested_action: RecoveryAction | None = None
    policy_outcome: PolicyOutcome
    effective_action: RecoveryAction | None = None
    payment_state: str
    event_trust_state: str
    model_output_valid: bool
    rules_evaluated: tuple[str, ...]
    rules_triggered: tuple[str, ...]
    final_reason_code: PolicyReasonCode
    reason_detail: str
    approval_required: bool
    approval_reference: str | None = None
    reconciliation_required: bool
    idempotency_key: str | None = None
    policy_version: str = Field(default=POLICY_VERSION)
    rule_set_version: str = Field(default=RULE_SET_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    decision_schema_version: str = Field(default=POLICY_DECISION_SCHEMA_VERSION)
    trace_schema_version: str = Field(default=POLICY_TRACE_SCHEMA_VERSION)
    decision_model_version: str
    diagnosis_model_version: str
    outcome_model_version: str
    dataset_version: str | None = None
    evaluation_run_id: str | None = None
    evaluated_at: datetime
    evaluation_latency_ms: float = Field(default=0.0, ge=0.0)


__all__ = ["PolicyEvaluationTrace"]
