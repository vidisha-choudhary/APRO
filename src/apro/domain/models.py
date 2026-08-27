"""Domain entity contracts and historical records for APRO."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.domain.enums import (
    AuditActor,
    ExecutionMode,
    ExecutionStatus,
    FailureCategory,
    OutcomeType,
    PaymentStatus,
    PolicyDecisionResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)

# ==============================================================================
# Mutable Current State Entities
# ==============================================================================


class Customer(BaseModel):
    """Represents a customer associated with payments."""

    customer_id: str
    external_reference: str | None = None
    created_at: datetime
    updated_at: datetime
    historical_payment_count: int = 0
    historical_success_count: int = 0
    historical_failure_count: int = 0
    historical_recovery_count: int = 0


class Payment(BaseModel):
    """Represents the current state of an external financial payment."""

    payment_id: str
    customer_id: str
    order_id: str | None = None
    provider: str
    amount: int
    currency: str
    method: str
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime
    captured_at: datetime | None = None
    failed_at: datetime | None = None


class RecoveryCase(BaseModel):
    """Represents APRO's recovery workflow state around a payment."""

    case_id: str
    payment_id: str
    customer_id: str
    status: RecoveryCaseStatus
    opened_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    recovery_amount: int | None = None
    current_attempt_count: int = 0
    stop_reason: str | None = None
    escalation_reason: str | None = None


class RecoveryAction(BaseModel):
    """Represents a candidate, approved, or executed recovery action."""

    action_id: str
    case_id: str
    action_type: RecoveryActionType
    status: RecoveryActionStatus
    created_at: datetime
    updated_at: datetime
    provider_reference: str | None = None
    execution_mode: ExecutionMode | None = None
    parameters: dict[str, Any] | None = None


class Execution(BaseModel):
    """Represents an attempt to perform an approved recovery action."""

    execution_id: str
    action_id: str
    case_id: str
    execution_type: str  # Kept as str per Architecture Lead Decision 1
    execution_mode: ExecutionMode
    status: ExecutionStatus
    provider_reference: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


# ==============================================================================
# Immutable Historical Record Entities (frozen=True)
# ==============================================================================


class PaymentEvent(BaseModel):
    """Immutable record of an observed payment-related event."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    provider: str
    event_type: str
    payment_id: str
    order_id: str | None = None
    amount: int
    currency: str
    method: str
    status: PaymentStatus
    failure_code: str | None = None
    failure_source: str | None = None
    failure_step: str | None = None
    failure_reason: str | None = None
    failure_description: str | None = None
    event_timestamp: datetime
    received_at: datetime
    raw_payload_reference: str | None = None


class Diagnosis(BaseModel):
    """Immutable record of an AI failure diagnosis prediction."""

    model_config = ConfigDict(frozen=True)

    diagnosis_id: str
    case_id: str
    category: FailureCategory
    confidence: float
    evidence: tuple[str, ...] = Field(default_factory=tuple)
    model_name: str
    model_version: str
    created_at: datetime


class ActionEvaluation(BaseModel):
    """Immutable record of an action evaluation model estimate."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str
    case_id: str
    action_type: RecoveryActionType
    success_probability: float
    recoverable_amount: int
    action_cost: int
    expected_recovery_value: int
    model_name: str
    model_version: str
    created_at: datetime


class Decision(BaseModel):
    """Immutable record of an AI recommendation decision."""

    model_config = ConfigDict(frozen=True)

    decision_id: str
    case_id: str
    recommended_action: RecoveryActionType
    confidence: float
    expected_recovery_value: int
    reason: str
    model_name: str
    model_version: str
    created_at: datetime


class PolicyDecision(BaseModel):
    """Immutable record of a deterministic governance policy evaluation."""

    model_config = ConfigDict(frozen=True)

    policy_decision_id: str
    decision_id: str
    case_id: str
    result: PolicyDecisionResult
    reason: str
    policy_version: str
    created_at: datetime


class Outcome(BaseModel):
    """Immutable record of an observed post-execution outcome."""

    model_config = ConfigDict(frozen=True)

    outcome_id: str
    case_id: str
    execution_id: str
    type: OutcomeType
    amount_recovered: int
    evidence_reference: str | None = None
    observed_at: datetime


class AuditEvent(BaseModel):
    """Immutable audit trail log event."""

    model_config = ConfigDict(frozen=True)

    audit_event_id: str
    case_id: str
    event_type: str
    actor: AuditActor
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
