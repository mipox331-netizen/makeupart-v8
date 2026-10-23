"""reopen free plans that were suspended by a stamped period end

Revision ID: 0011_reopen_free_plan
Revises: 0010_nullable_similarity
Create Date: 2026-10-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011_reopen_free_plan"
down_revision: Union[str, None] = "0010_nullable_similarity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE subscriptions "
            "SET status = 'active', current_period_end = NULL "
            "WHERE lower(plan) = 'free' "
            "AND (lower(status) <> 'active' OR current_period_end IS NOT NULL)"
        )
    )


def downgrade() -> None:
    pass
