"""align one-to-one uniqueness indexes with ORM metadata

Revision ID: 0008_align_unique_indexes
Revises: 0007_login_rate_limits
Create Date: 2026-10-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008_align_unique_indexes"
down_revision: Union[str, None] = "0007_login_rate_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These columns were historically represented as a UNIQUE constraint plus
    # a separate non-unique index. SQLAlchemy metadata represents each as a
    # unique index (unique=True, index=True). Existing unique constraints
    # already guarantee there are no duplicate values before this conversion.
    for table, column, constraint, index in (
        ("beauty_results", "beauty_job_id", "beauty_results_beauty_job_id_key", "ix_beauty_results_beauty_job_id"),
        ("subscriptions", "salon_id", "subscriptions_salon_id_key", "ix_subscriptions_salon_id"),
        ("watermarks", "salon_id", "watermarks_salon_id_key", "ix_watermarks_salon_id"),
    ):
        op.drop_constraint(constraint, table, type_="unique")
        op.drop_index(index, table_name=table)
        op.create_index(index, table, [column], unique=True)


def downgrade() -> None:
    for table, column, constraint, index in (
        ("beauty_results", "beauty_job_id", "beauty_results_beauty_job_id_key", "ix_beauty_results_beauty_job_id"),
        ("subscriptions", "salon_id", "subscriptions_salon_id_key", "ix_subscriptions_salon_id"),
        ("watermarks", "salon_id", "watermarks_salon_id_key", "ix_watermarks_salon_id"),
    ):
        op.drop_index(index, table_name=table)
        op.create_unique_constraint(constraint, table, [column])
        op.create_index(index, table, [column], unique=False)
