"""add subscription usage counters for beauty quotas

Revision ID: 0004_subscription_usage
Revises: 0003_refresh_sessions
Create Date: 2026-09-30
"""
from datetime import date
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_subscription_usage"
down_revision: Union[str, None] = "0003_refresh_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("usage_period_start", sa.Date(), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("beauty_jobs_used", sa.Integer(), nullable=True),
    )

    bind = op.get_bind()
    today = date.today().replace(day=1)

    op.execute(
        sa.text(
            "UPDATE subscriptions "
            "SET usage_period_start = :period_start, beauty_jobs_used = 0 "
            "WHERE usage_period_start IS NULL OR beauty_jobs_used IS NULL"
        ).bindparams(period_start=today)
    )

    salon_rows = bind.execute(
        sa.text(
            """
            SELECT s.id, lower(s.subscription_plan::text) AS plan
            FROM salons s
            LEFT JOIN subscriptions sub ON sub.salon_id = s.id
            WHERE sub.id IS NULL
            """
        )
    ).mappings().all()

    for row in salon_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO subscriptions
                    (id, salon_id, plan, status, usage_period_start, beauty_jobs_used, created_at, updated_at)
                VALUES
                    (:id, :salon_id, :plan, 'active', :period_start, 0, now(), now())
                """
            ),
            {
                "id": uuid.uuid4(),
                "salon_id": row["id"],
                "plan": row["plan"],
                "period_start": today,
            },
        )

    op.alter_column(
        "subscriptions",
        "usage_period_start",
        nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "beauty_jobs_used",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "beauty_jobs_used")
    op.drop_column("subscriptions", "usage_period_start")
