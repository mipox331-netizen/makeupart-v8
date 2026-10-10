"""keep users.token_version compatible with existing production schema

Revision ID: 0008_user_token_version
Revises: 0007_login_rate_limits
Create Date: 2026-10-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_user_token_version"
down_revision: Union[str, None] = "0007_login_rate_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}

    if "token_version" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "token_version",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            ),
        )
        return

    # The production database already contains this legacy column but no default,
    # which caused account creation to fail with a PostgreSQL NOT NULL violation.
    op.execute(sa.text("UPDATE users SET token_version = 0 WHERE token_version IS NULL"))
    op.alter_column(
        "users",
        "token_version",
        existing_type=sa.Integer(),
        server_default=sa.text("0"),
        nullable=False,
    )


def downgrade() -> None:
    # Intentionally retain the compatibility column: it may predate Alembic in
    # production, and removing it could break deployments that still rely on it.
    pass
