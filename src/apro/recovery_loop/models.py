"""Pydantic models for APRO Phase 13 Recovery Loop."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apro.dataset.models import ModelInputRecord
from apro.decision.models import RecoveryDecision
from apro.domain.enums import (
    ExecutionStatus,
    OutcomeType,
    PaymentStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from apro.domain.models import Diagnosis, Outcome, Payment
from apro.execution.models import ExecutionResult
from apro.policy.models import PolicyDecision
from apro.recovery_loop.enums import (
    EvidenceProvenance,
    EvidenceType,
    LoopTerminationReason,
    RecoveryLoopDisposition,
)

_FORBIDDEN_DETAIL_KEYS = {
    "key_secret",
    "secret",
    "password",
    "token",
    "authorization",
    "rzp_test_secret",
    "rzp_live_secret",
    "potential_outcomes",
    "oracle_action",
    "hidden_recoverability",
    "latent",
    "latent_state",
    "hidden_state",
    "best_achievable",
    "true_action_probabilities",
    "true_failure_mechanism",
}


def _sanitize_details(d: dict[str, Any]) -> dict[str, Any]:
    """Sanitize raw detail dictionary to remove secrets and latent simulator truth."""
    sanitized: dict[str, Any] = {}
    for k, v in d.items():
        k_lower = str(k).lower()
        if any(bad in k_lower for bad in _FORBIDDEN_DETAIL_KEYS):
            continue
        if isinstance(v, dict):
            sanitized[k] = _sanitize_details(v)
        else:
            sanitized[k] = v
    return sanitized


class OutcomeEvidence(BaseModel):
    """Normalized evidence presented to the recovery loop for outcome processing."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    case_id: str
    execution_id: str | None = None
    evidence_type: EvidenceType
    payment_status: PaymentStatus | None = None
    amount_recovered: int = 0
    evidence_reference: str | None = None
    observed_at: datetime
    provenance: EvidenceProvenance | str = EvidenceProvenance.SYSTEM
    raw_details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_details")
    @classmethod
    def sanitize_raw_details(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _sanitize_details(v)

    @field_validator("amount_recovered")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v < 0:
            msg = "amount_recovered cannot be negative."
            raise ValueError(msg)
        return v


class ActionHistoryRecord(BaseModel):
    """Immutable record of an attempted recovery action and its outcome."""

    model_config = ConfigDict(frozen=True)

    action_id: str
    action_type: RecoveryActionType
    execution_id: str | None = None
    execution_status: ExecutionStatus | None = None
    outcome_type: OutcomeType | None = None
    amount_recovered: int = 0
    observed_at: datetime
    attempt_order: int = 1
    provider_reference: str | None = None


class OutcomeProcessingResult(BaseModel):
    """Result of processing an outcome evidence item."""

    model_config = ConfigDict(frozen=True)

    outcome: Outcome
    disposition: RecoveryLoopDisposition
    case_status: RecoveryCaseStatus
    re_evaluation_id: str | None = None
    termination_reason: LoopTerminationReason | None = None
    cycle_number: int = 1
    provenance: EvidenceProvenance = EvidenceProvenance.SYSTEM


class ReEvaluationContext(BaseModel):
    """Observable context for initiating a fresh decision cycle."""

    model_config = ConfigDict(frozen=True)

    re_evaluation_id: str
    case_id: str
    payment: Payment
    cycle_number: int
    history: tuple[ActionHistoryRecord, ...] = Field(default_factory=tuple)
    latest_diagnosis: Diagnosis | None = None
    latest_outcome: Outcome | None = None
    model_input: ModelInputRecord
    created_at: datetime


class AdaptiveCycleResult(BaseModel):
    """Complete summary of a single cycle in the adaptive recovery loop."""

    model_config = ConfigDict(frozen=True)

    cycle_number: int
    re_evaluation_id: str | None = None
    outcome_result: OutcomeProcessingResult
    decision: RecoveryDecision | None = None
    policy_decision: PolicyDecision | None = None
    execution_result: ExecutionResult | None = None
