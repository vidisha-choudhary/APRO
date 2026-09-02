"""Data models, history containers, and policy decision records for Phase 10."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.domain.enums import (
    PaymentStatus,
    PolicyDecisionResult,
)
from apro.domain.models import PolicyDecision as DomainPolicyDecision
from apro.policy.enums import (
    POLICY_DECISION_SCHEMA_VERSION,
    POLICY_VERSION,
    RULE_SET_VERSION,
    PolicyOutcome,
    PolicyReasonCode,
)
from apro.recovery_prediction.enums import (
    RECOVERY_ACTION_SCHEMA_VERSION,
    RecoveryAction,
)


class EventTrustState(StrEnum):
    """Cryptographic trust evaluation state of the triggering event."""

    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
    UNKNOWN = "UNKNOWN"


class ActionExecutionHistory(BaseModel):
    """Historical execution context and action counters for a recovery case."""

    model_config = ConfigDict(frozen=True)

    retry_count: int = Field(default=0, ge=0)
    last_retry_at: datetime | None = None
    same_action_count: int = Field(default=0, ge=0)
    last_action: RecoveryAction | None = None
    total_interventions: int = Field(default=0, ge=0)
    payment_link_count: int = Field(default=0, ge=0)
    executed_idempotency_keys: tuple[str, ...] = Field(default_factory=tuple)
    executed_approval_ids: tuple[str, ...] = Field(default_factory=tuple)


class ApprovalRecord(BaseModel):
    """Immutable human approval record binding a specific case, decision, action."""

    model_config = ConfigDict(frozen=True)

    approval_id: str
    case_id: str
    decision_id: str
    approved_action: RecoveryAction
    approver_reference: str
    approved_at: datetime
    expires_at: datetime | None = None
    policy_version: str = Field(default=POLICY_VERSION)


class IdempotencyIdentity(BaseModel):
    """Deterministic internal idempotency identity for action authorization."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    action: RecoveryAction
    execution_attempt: int = Field(ge=1)
    key: str


class PolicyDecision(BaseModel):
    """Immutable, auditable runtime policy governance evaluation decision."""

    model_config = ConfigDict(frozen=True)

    policy_decision_id: str
    case_id: str
    payment_id: str
    event_id: str | None = None
    decision_id: str | None = None
    requested_action: RecoveryAction | None = None
    policy_outcome: PolicyOutcome
    effective_action: RecoveryAction | None = None
    reason_code: PolicyReasonCode
    reason_detail: str
    approval_required: bool = False
    approval_reference: str | None = None
    reconciliation_required: bool = False
    defer_until: datetime | None = None
    idempotency_key: str | None = None
    rules_evaluated: tuple[str, ...] = Field(default_factory=tuple)
    rules_triggered: tuple[str, ...] = Field(default_factory=tuple)
    payment_state_observed: PaymentStatus
    event_trust_state: str = EventTrustState.TRUSTED.value
    model_output_valid: bool = True
    policy_version: str = Field(default=POLICY_VERSION)
    rule_set_version: str = Field(default=RULE_SET_VERSION)
    action_schema_version: str = Field(default=RECOVERY_ACTION_SCHEMA_VERSION)
    decision_schema_version: str = Field(default=POLICY_DECISION_SCHEMA_VERSION)
    decision_model_version: str
    diagnosis_model_version: str
    outcome_model_version: str
    dataset_version: str | None = None
    evaluation_run_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    def to_domain(self) -> DomainPolicyDecision:
        """Convert Phase 10 PolicyDecision to Phase 1 domain entity."""
        domain_result = (
            PolicyDecisionResult.ALLOW
            if self.policy_outcome == PolicyOutcome.ALLOW
            else PolicyDecisionResult.REQUIRE_HUMAN_APPROVAL
            if self.policy_outcome == PolicyOutcome.REQUIRE_HUMAN_APPROVAL
            else PolicyDecisionResult.BLOCK
        )
        return DomainPolicyDecision(
            policy_decision_id=self.policy_decision_id,
            decision_id=self.decision_id or "",
            case_id=self.case_id,
            result=domain_result,
            reason=f"{self.reason_code.value}: {self.reason_detail}",
            policy_version=self.policy_version,
            created_at=self.created_at,
        )


__all__ = [
    "ActionExecutionHistory",
    "ApprovalRecord",
    "EventTrustState",
    "IdempotencyIdentity",
    "PolicyDecision",
]
