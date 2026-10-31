"""add selectable text and logo watermark content modes

Revision ID: 0013_watermark_content
Revises: 0012_payment_ledger
Create Date: 2026-10-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_watermark_content"
down_revision: Union[str, None] = "0012_payment_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Preserve the previous behavior for salons that already use watermarks.
    op.add_column(
        "watermarks",
        sa.Column("watermark_text", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "watermarks",
        sa.Column(
            "content_mode",
            sa.String(length=10),
            nullable=False,
            server_default="both",
        ),
    )
    op.create_check_constraint(
        "ck_watermarks_content_mode",
        "watermarks",
        "content_mode IN ('text', 'logo', 'both')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_watermarks_content_mode",
        "watermarks",
        type_="check",
    )
    op.drop_column("watermarks", "content_mode")
    op.drop_column("watermarks", "watermark_text")
