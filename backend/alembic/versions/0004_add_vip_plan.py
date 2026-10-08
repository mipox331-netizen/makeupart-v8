"""compatibility no-op for the legacy production Alembic revision.

Revision ID: 0004_add_vip_plan
Revises: 0003_refresh_sessions

This revision existed in an earlier production migration history. The current
application schema already defines the subscription plan as a string, so no
schema mutation is required here. Keeping the revision ID allows existing
databases stamped at this revision to migrate safely into the current chain.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_add_vip_plan"
down_revision: Union[str, None] = "0003_refresh_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
