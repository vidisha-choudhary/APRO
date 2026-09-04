"""Enforce PostgreSQL trigger for audit_events append-only immutability

Revision ID: 003_audit_events_immutability
Revises: 002_add_provider_payment_id
Create Date: 2026-09-04 02:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_audit_events_immutability"
down_revision: str | None = "002_add_provider_payment_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_events_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION
                    'audit_events is append-only: % operation not permitted on %',
                    TG_OP, OLD.audit_event_id;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_audit_events_immutability ON audit_events;"
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_events_immutability
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_events_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_audit_events_immutability ON audit_events;"
        )
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_events_mutation();")
