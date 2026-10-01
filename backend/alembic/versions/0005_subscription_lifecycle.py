"""add subscription lifecycle end date

Revision ID: 0005_subscription_lifecycle
Revises: 0004_subscription_usage
Create Date: 2026-10-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_subscription_lifecycle"
down_revision: Union[str, None] = "0004_subscription_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE subscriptions "
            "SET current_period_end = updated_at + interval '30 days' "
            "WHERE current_period_end IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "current_period_end")
