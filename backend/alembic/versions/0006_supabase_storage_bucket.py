"""reserve the revision slot for Supabase Storage integration.

Revision ID: 0006_supabase_storage_bucket
Revises: 0005_subscription_lifecycle

The production API currently persists generated media on the Modal volume.
Supabase Storage is intentionally not mutated from Alembic because Supabase
documents the storage schema as service-managed/read-only metadata. A future
storage integration should create/manage the bucket through the Storage API.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006_supabase_storage_bucket"
down_revision: Union[str, None] = "0005_subscription_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally a no-op. The revision reserves the schema slot without
    # mutating Supabase-managed storage metadata.
    pass


def downgrade() -> None:
    # Nothing was created by this revision.
    pass
