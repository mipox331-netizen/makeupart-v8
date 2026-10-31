"""reconcile nullable beauty-job media path columns

Revision ID: 0014_reconcile_beauty_media_paths
Revises: 0013_watermark_content
Create Date: 2026-10-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_reconcile_beauty_media_paths"
down_revision: Union[str, None] = "0013_watermark_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable path columns only where older production schemas lack them.

    These fields were part of the original application model. A small number of
    production databases reached the current Alembic revision without them.
    The migration is intentionally idempotent and never rewrites existing rows.
    """
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("beauty_jobs")}

    if "input_file_path" not in existing:
        op.add_column(
            "beauty_jobs",
            sa.Column("input_file_path", sa.String(length=2000), nullable=True),
        )
    if "output_file_path" not in existing:
        op.add_column(
            "beauty_jobs",
            sa.Column("output_file_path", sa.String(length=2000), nullable=True),
        )


def downgrade() -> None:
    # This migration converges older databases to the original ORM schema.
    # It cannot safely drop columns on installations where they predated 0014.
    pass
