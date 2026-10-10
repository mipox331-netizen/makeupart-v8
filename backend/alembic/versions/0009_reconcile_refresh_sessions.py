"""reconcile a missing refresh_sessions table in production

Revision ID: 0009_reconcile_refresh_sessions
Revises: 0008_user_token_version
Create Date: 2026-10-10

Some production databases were stamped at a newer Alembic revision while this
required authentication table was absent. Recreate it only when missing.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_reconcile_refresh_sessions"
down_revision: Union[str, None] = "0008_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "refresh_sessions" not in inspector.get_table_names():
        op.create_table(
            "refresh_sessions",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    indexes = {index["name"] for index in inspector.get_indexes("refresh_sessions")}
    if "ix_refresh_sessions_user_id" not in indexes:
        op.create_index(
            "ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"], unique=False
        )
    if "ix_refresh_sessions_token_hash" not in indexes:
        op.create_index(
            "ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"], unique=True
        )


def downgrade() -> None:
    # Retain auth history in production; restoring this table is a safe reconciliation.
    pass
