"""Initial Phase 2 schema creation with UUID primary keys and JSONB raw payload

Revision ID: 001_initial_phase_02_schema
Revises:
Create Date: 2026-08-27 20:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_phase_02_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Cross-dialect type helpers for Alembic DDL
UUID_TYPE = sa.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")
JSONB_TYPE = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    # 1. customers
    op.create_table(
        "customers",
        sa.Column("customer_id", UUID_TYPE, nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "historical_payment_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "historical_success_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "historical_failure_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "historical_recovery_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.PrimaryKeyConstraint("customer_id"),
    )

    # 2. payments
    op.create_table(
        "payments",
        sa.Column("payment_id", UUID_TYPE, nullable=False),
        sa.Column("customer_id", UUID_TYPE, nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.PrimaryKeyConstraint("payment_id"),
    )
    op.create_index(
        op.f("ix_payments_customer_id"), "payments", ["customer_id"], unique=False
    )
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)

    # 3. raw_events
    op.create_table(
        "raw_events",
        sa.Column("raw_event_id", UUID_TYPE, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", JSONB_TYPE, nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=32),
            nullable=False,
            server_default="VERIFIED",
        ),
        sa.PrimaryKeyConstraint("raw_event_id"),
        sa.UniqueConstraint(
            "provider", "provider_event_id", name="uq_raw_events_provider_event_id"
        ),
    )

    # 4. payment_events
    op.create_table(
        "payment_events",
        sa.Column("event_id", UUID_TYPE, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payment_id", UUID_TYPE, nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_source", sa.String(length=128), nullable=True),
        sa.Column("failure_step", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.String(length=128), nullable=True),
        sa.Column("failure_description", sa.Text(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_reference", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.payment_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        op.f("ix_payment_events_payment_id"),
        "payment_events",
        ["payment_id"],
        unique=False,
    )

    # 5. recovery_cases
    op.create_table(
        "recovery_cases",
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("payment_id", UUID_TYPE, nullable=False),
        sa.Column("customer_id", UUID_TYPE, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovery_amount", sa.BigInteger(), nullable=True),
        sa.Column(
            "current_attempt_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.payment_id"]),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index(
        op.f("ix_recovery_cases_customer_id"),
        "recovery_cases",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recovery_cases_payment_id"),
        "recovery_cases",
        ["payment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recovery_cases_status"), "recovery_cases", ["status"], unique=False
    )

    # 6. recovery_actions
    op.create_table(
        "recovery_actions",
        sa.Column("action_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("execution_mode", sa.String(length=32), nullable=True),
        sa.Column("parameters", JSONB_TYPE, nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("action_id"),
    )
    op.create_index(
        op.f("ix_recovery_actions_case_id"),
        "recovery_actions",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recovery_actions_status"), "recovery_actions", ["status"], unique=False
    )

    # 7. diagnoses
    op.create_table(
        "diagnoses",
        sa.Column("diagnosis_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", JSONB_TYPE, nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("diagnosis_id"),
    )
    op.create_index(
        op.f("ix_diagnoses_case_id"), "diagnoses", ["case_id"], unique=False
    )

    # 8. action_evaluations
    op.create_table(
        "action_evaluations",
        sa.Column("evaluation_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("success_probability", sa.Float(), nullable=False),
        sa.Column("recoverable_amount", sa.BigInteger(), nullable=False),
        sa.Column("action_cost", sa.BigInteger(), nullable=False),
        sa.Column("expected_recovery_value", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("evaluation_id"),
    )
    op.create_index(
        op.f("ix_action_evaluations_case_id"),
        "action_evaluations",
        ["case_id"],
        unique=False,
    )

    # 9. decisions
    op.create_table(
        "decisions",
        sa.Column("decision_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("expected_recovery_value", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index(
        op.f("ix_decisions_case_id"), "decisions", ["case_id"], unique=False
    )

    # 10. policy_decisions
    op.create_table(
        "policy_decisions",
        sa.Column("policy_decision_id", UUID_TYPE, nullable=False),
        sa.Column("decision_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.decision_id"]),
        sa.PrimaryKeyConstraint("policy_decision_id"),
    )
    op.create_index(
        op.f("ix_policy_decisions_case_id"),
        "policy_decisions",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_decisions_decision_id"),
        "policy_decisions",
        ["decision_id"],
        unique=False,
    )

    # 11. executions
    op.create_table(
        "executions",
        sa.Column("execution_id", UUID_TYPE, nullable=False),
        sa.Column("action_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("execution_type", sa.String(length=64), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["action_id"], ["recovery_actions.action_id"]),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("execution_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_executions_idempotency_key"),
    )
    op.create_index(
        op.f("ix_executions_action_id"), "executions", ["action_id"], unique=False
    )
    op.create_index(
        op.f("ix_executions_case_id"), "executions", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_executions_status"), "executions", ["status"], unique=False
    )

    # 12. outcomes
    op.create_table(
        "outcomes",
        sa.Column("outcome_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("execution_id", UUID_TYPE, nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount_recovered", sa.BigInteger(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=128), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.execution_id"]),
        sa.PrimaryKeyConstraint("outcome_id"),
    )
    op.create_index(op.f("ix_outcomes_case_id"), "outcomes", ["case_id"], unique=False)
    op.create_index(
        op.f("ix_outcomes_execution_id"), "outcomes", ["execution_id"], unique=False
    )

    # 13. audit_events
    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", UUID_TYPE, nullable=False),
        sa.Column("case_id", UUID_TYPE, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", JSONB_TYPE, nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["recovery_cases.case_id"]),
        sa.PrimaryKeyConstraint("audit_event_id"),
    )
    op.create_index(
        op.f("ix_audit_events_case_id"), "audit_events", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_timestamp"), "audit_events", ["timestamp"], unique=False
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("outcomes")
    op.drop_table("executions")
    op.drop_table("policy_decisions")
    op.drop_table("decisions")
    op.drop_table("action_evaluations")
    op.drop_table("diagnoses")
    op.drop_table("recovery_actions")
    op.drop_table("recovery_cases")
    op.drop_table("payment_events")
    op.drop_table("raw_events")
    op.drop_table("payments")
    op.drop_table("customers")
