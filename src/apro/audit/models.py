"""Data models and trace structures for Phase 14 Audit & Observability."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apro.audit.enums import (
    AUDIT_SCHEMA_VERSION,
    AuditCompleteness,
)
from apro.domain.models import AuditEvent


class StructuredLogEntry(BaseModel):
    """Structured operational log entry for JSON output."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    level: str
    service: str = "apro"
    event_name: str
    case_id: str | None = None
    trace_id: str | None = None
    cycle_id: int | str | None = None
    entity_id: str | None = None
    phase: str | None = None
    status: str | None = None
    reason_code: str | None = None
    duration_ms: float | None = None
    exception_type: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionTraceRecord(BaseModel):
    """Reconstructed decision provenance record."""

    model_config = ConfigDict(frozen=True)

    decision_id: str
    case_id: str
    cycle_number: int = 1
    model_name: str = "decision_engine"
    model_version: str = "1.0.0"
    dataset_version: str = "dataset-v1"
    feature_schema_version: str = "1.0"
    input_features_summary: dict[str, Any] = Field(default_factory=dict)
    diagnosis_ref: dict[str, Any] | None = None
    prediction_refs: list[dict[str, Any]] = Field(default_factory=list)
    candidate_actions: list[dict[str, Any]] = Field(default_factory=list)
    selected_action: str
    expected_recovery_value: int | float | None = None
    created_at: datetime


class PolicyTraceRecord(BaseModel):
    """Reconstructed policy decision provenance record."""

    model_config = ConfigDict(frozen=True)

    policy_decision_id: str
    case_id: str
    decision_id: str
    policy_version: str = "1.0.0"
    ruleset_version: str = "policy-rules-v1"
    policy_outcome: str
    effective_action: str
    reason_code: str
    reason_detail: str | None = None
    rules_triggered: list[str] = Field(default_factory=list)
    human_approval_required: bool = False
    approval_id: str | None = None
    created_at: datetime


class ExecutionTraceRecord(BaseModel):
    """Reconstructed execution provenance record."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    case_id: str
    action_id: str
    execution_mode: str
    executor_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    error_code: str | None = None
    provider_reference: str | None = None


class OutcomeTraceRecord(BaseModel):
    """Reconstructed outcome provenance record."""

    model_config = ConfigDict(frozen=True)

    outcome_id: str
    case_id: str
    execution_id: str
    outcome_type: str
    amount_recovered: int = 0
    evidence_reference: str | None = None
    provenance: str = "SIMULATOR"
    observed_at: datetime


class CycleTraceRecord(BaseModel):
    """Reconstructed cycle record grouping events for one adaptive loop cycle."""

    model_config = ConfigDict(frozen=True)

    cycle_number: int
    re_evaluation_id: str | None = None
    decision: DecisionTraceRecord | None = None
    policy: PolicyTraceRecord | None = None
    execution: ExecutionTraceRecord | None = None
    outcome: OutcomeTraceRecord | None = None
    events: list[AuditEvent] = Field(default_factory=list)


class CaseAuditTrace(BaseModel):
    """Complete, causally reconstructable audit trace for one recovery case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    trace_id: str | None = None
    schema_version: str = AUDIT_SCHEMA_VERSION
    initial_event: dict[str, Any] | None = None
    diagnosis: dict[str, Any] | None = None
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    cycles: list[CycleTraceRecord] = Field(default_factory=list)
    events: list[AuditEvent] = Field(default_factory=list)
    final_case_status: str
    final_outcome_type: str | None = None
    total_amount_recovered: int = 0
    completeness: AuditCompleteness = AuditCompleteness.COMPLETE
    integrity_valid: bool = True
    integrity_issues: list[str] = Field(default_factory=list)
    reviewer_answers: dict[str, Any] = Field(default_factory=dict)
