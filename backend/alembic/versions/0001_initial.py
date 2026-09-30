"""initial schema: salons and users

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    subscription_plan = postgresql.ENUM(
        "FREE", "BASIC", "PRO", "ENTERPRISE", name="subscription_plan", create_type=False
    )
    user_role = postgresql.ENUM(
        "OWNER", "STAFF", "ADMIN", name="user_role", create_type=False
    )
    subscription_plan.create(bind, checkfirst=True)
    user_role.create(bind, checkfirst=True)

    op.create_table(
        "salons",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("instagram", sa.String(100), nullable=True),
        sa.Column("tiktok", sa.String(100), nullable=True),
        sa.Column("facebook", sa.String(100), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("subscription_plan", subscription_plan, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "salon_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("salons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("salons")

    bind = op.get_bind()
    postgresql.ENUM(name="user_role").drop(bind, checkfirst=True)
    postgresql.ENUM(name="subscription_plan").drop(bind, checkfirst=True)
