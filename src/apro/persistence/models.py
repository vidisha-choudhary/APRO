"""SQLAlchemy ORM models for APRO Phase 2 persistence."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apro.persistence.base import Base

# Cross-dialect type helpers
UUID_TYPE = UUID(as_uuid=False).with_variant(String(36), "sqlite")
JSONB_TYPE = JSONB().with_variant(JSON(), "sqlite")


class CustomerModel(Base):
    """Durable customer ORM model."""

    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    historical_payment_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    historical_success_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    historical_failure_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    historical_recovery_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )


class PaymentModel(Base):
    """Durable current payment ORM model."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_payment_id", name="uq_payments_provider_payment_id"
        ),
    )

    payment_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Minor units (paise)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RawEventModel(Base):
    """Durable raw provider event ORM model."""

    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_raw_events_provider_event_id"
        ),
    )

    raw_event_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="VERIFIED", nullable=False
    )


class PaymentEventModel(Base):
    """Canonicalized historical payment event ORM model."""

    __tablename__ = "payment_events"

    event_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("payments.payment_id"), nullable=False, index=True
    )
    order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_payload_reference: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )


class RecoveryCaseModel(Base):
    """Durable recovery case ORM model."""

    __tablename__ = "recovery_cases"

    case_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    payment_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("payments.payment_id"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        UUID_TYPE, ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_attempt_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecoveryActionModel(Base):
    """Durable recovery action ORM model."""

    __tablename__ = "recovery_actions"

    action_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB_TYPE, nullable=True)


class DiagnosisModel(Base):
    """Immutable failure diagnosis ORM model."""

    __tablename__ = "diagnoses"

    diagnosis_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSONB_TYPE, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ActionEvaluationModel(Base):
    """Immutable action evaluation ORM model."""

    __tablename__ = "action_evaluations"

    evaluation_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    success_probability: Mapped[float] = mapped_column(Float, nullable=False)
    recoverable_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action_cost: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_recovery_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionModel(Base):
    """Immutable decision ORM model."""

    __tablename__ = "decisions"

    decision_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    expected_recovery_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class PolicyDecisionModel(Base):
    """Immutable policy decision ORM model."""

    __tablename__ = "policy_decisions"

    policy_decision_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("decisions.decision_id"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ExecutionModel(Base):
    """Durable execution attempt ORM model."""

    __tablename__ = "executions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_executions_idempotency_key"),
    )

    execution_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    action_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_actions.action_id"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    execution_type: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class OutcomeModel(Base):
    """Immutable observed outcome ORM model."""

    __tablename__ = "outcomes"

    outcome_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("executions.execution_id"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_recovered: Mapped[int] = mapped_column(BigInteger, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AuditEventModel(Base):
    """Immutable audit log event ORM model."""

    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True)
    case_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


@event.listens_for(AuditEventModel, "before_update")
def _prevent_audit_event_update(_mapper: Any, _connection: Any, target: Any) -> None:
    from apro.audit.exceptions import AuditImmutabilityError

    ev_id = getattr(target, "audit_event_id", "")
    raise AuditImmutabilityError(
        f"AuditEventModel {ev_id} is immutable and cannot be updated."
    )


@event.listens_for(AuditEventModel, "before_delete")
def _prevent_audit_event_delete(_mapper: Any, _connection: Any, target: Any) -> None:
    from apro.audit.exceptions import AuditImmutabilityError

    ev_id = getattr(target, "audit_event_id", "")
    raise AuditImmutabilityError(
        f"AuditEventModel {ev_id} is immutable and cannot be deleted."
    )
