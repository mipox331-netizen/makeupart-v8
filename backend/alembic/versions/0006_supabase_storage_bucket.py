"""provision Supabase Storage bucket when running against Supabase.

Revision ID: 0006_supabase_storage_bucket
Revises: 0005_subscription_lifecycle
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006_supabase_storage_bucket"
down_revision: Union[str, None] = "0005_subscription_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUCKET_ID = "makeupart-media"


def upgrade() -> None:
    # Supabase exposes the storage schema/table in the managed PostgreSQL
    # project. Keep this migration portable so local PostgreSQL CI does not fail.
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM pg_namespace
            WHERE nspname = 'storage'
          ) AND EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'storage'
              AND table_name = 'buckets'
          ) THEN
            INSERT INTO storage.buckets (id, name, public)
            VALUES ('{BUCKET_ID}', '{BUCKET_ID}', FALSE)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                public = FALSE;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM pg_namespace
            WHERE nspname = 'storage'
          ) AND EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'storage'
              AND table_name = 'buckets'
          ) THEN
            DELETE FROM storage.buckets WHERE id = '{BUCKET_ID}';
          END IF;
        END $$;
        """
    )
