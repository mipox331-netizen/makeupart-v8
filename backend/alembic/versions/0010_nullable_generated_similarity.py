"""Allow generated beauty edits without a misleading similarity score.

Revision ID: 0010_nullable_similarity
Revises: 0009_reconcile_refresh_sessions
Create Date: 2026-10-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_nullable_similarity"
down_revision: Union[str, None] = "0009_reconcile_refresh_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "beauty_results" not in tables:
        raise RuntimeError("Required beauty_results table is missing.")
    columns = {column["name"]: column for column in inspector.get_columns("beauty_results")}
    column = columns.get("identity_similarity")
    if column is None:
        raise RuntimeError("Required beauty_results.identity_similarity column is missing.")
    if not column["nullable"]:
        op.alter_column(
            "beauty_results",
            "identity_similarity",
            existing_type=sa.Float(),
            existing_nullable=False,
            nullable=True,
        )


def downgrade() -> None:
    # Older schema requires a numeric score. Backfill only unavailable generated
    # scores before restoring NOT NULL; zero remains an explicit legacy sentinel.
    op.execute(
        sa.text("UPDATE beauty_results SET identity_similarity = 0.0 "
                "WHERE identity_similarity IS NULL")
    )
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns("beauty_results")}
    column = columns.get("identity_similarity")
    if column is not None and column["nullable"]:
        op.alter_column(
            "beauty_results",
            "identity_similarity",
            existing_type=sa.Float(),
            existing_nullable=True,
            nullable=False,
        )
