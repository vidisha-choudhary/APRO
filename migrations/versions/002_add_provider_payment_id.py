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
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(
            sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
        )
        batch_op.create_unique_constraint(
            "uq_payments_provider_payment_id",
            ["provider", "provider_payment_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("uq_payments_provider_payment_id", type_="unique")
        batch_op.drop_column("provider_payment_id")
