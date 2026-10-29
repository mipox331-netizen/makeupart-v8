"""add manually verified payment ledger

Revision ID: 0012_payment_ledger
Revises: 0011_reopen_free_plan
Create Date: 2026-10-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_payment_ledger"
down_revision: Union[str, None] = "0011_reopen_free_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_records",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("subscription_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("recorded_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TZS"),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="confirmed"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_records_amount_positive"),
        sa.CheckConstraint("period_days > 0", name="ck_payment_records_period_positive"),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_method", "reference", name="uq_payment_records_method_reference"),
    )
    op.create_index(
        "ix_payment_records_received_status",
        "payment_records",
        ["received_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_payment_records_salon_received",
        "payment_records",
        ["salon_id", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_records_salon_received", table_name="payment_records")
    op.drop_index("ix_payment_records_received_status", table_name="payment_records")
    op.drop_table("payment_records")
