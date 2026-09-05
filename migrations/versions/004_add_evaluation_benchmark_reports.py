"""Add evaluation_benchmark_reports table for durable Phase 15 benchmark artifacts

Revision ID: 004_add_evaluation_benchmark_reports
Revises: 003_audit_events_immutability
Create Date: 2026-09-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_eval_benchmark_reports"
down_revision: str | None = "003_audit_events_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(
        sa.JSON(), "sqlite"
    )

    op.create_table(
        "evaluation_benchmark_reports",
        sa.Column("report_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "benchmark_run_id",
            sa.String(length=128),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("evaluation_config_version", sa.String(length=64), nullable=False),
        sa.Column("metric_schema_version", sa.String(length=64), nullable=False),
        sa.Column("code_revision", sa.String(length=128), nullable=False),
        sa.Column("bootstrap_seed", sa.Integer(), nullable=False),
        sa.Column("bootstrap_iterations", sa.Integer(), nullable=False),
        sa.Column("report_hash", sa.String(length=64), index=True, nullable=False),
        sa.Column("recovery_rate", sa.Float(), nullable=False),
        sa.Column("gross_recovered_amount", sa.BigInteger(), nullable=False),
        sa.Column("net_recovered_revenue", sa.BigInteger(), nullable=False),
        sa.Column("total_intervention_cost", sa.BigInteger(), nullable=False),
        sa.Column(
            "is_synthetic_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("report_payload", jsonb_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_evaluation_benchmark_reports_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION
                    'evaluation_benchmark_reports is append-only: % on %',
                    TG_OP, OLD.benchmark_run_id;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            "DROP TRIGGER IF EXISTS "
            "trg_evaluation_benchmark_reports_immutability "
            "ON evaluation_benchmark_reports;"
        )
        op.execute(
            """
            CREATE TRIGGER trg_evaluation_benchmark_reports_immutability
            BEFORE UPDATE OR DELETE ON evaluation_benchmark_reports
            FOR EACH ROW
            EXECUTE FUNCTION prevent_evaluation_benchmark_reports_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS "
            "trg_evaluation_benchmark_reports_immutability "
            "ON evaluation_benchmark_reports;"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS prevent_evaluation_benchmark_reports_mutation();"
        )
    op.drop_table("evaluation_benchmark_reports")
