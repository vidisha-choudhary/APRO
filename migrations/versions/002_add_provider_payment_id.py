"""Add provider_payment_id column and unique constraint to payments table

Revision ID: 002_add_provider_payment_id
Revises: 001_initial_phase_02_schema
Create Date: 2026-08-28 21:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_provider_payment_id"
down_revision: str | None = "001_initial_phase_02_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_payments_provider_payment_id",
        "payments",
        ["provider", "provider_payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payments_provider_payment_id", "payments", type_="unique")
    op.drop_column("payments", "provider_payment_id")
