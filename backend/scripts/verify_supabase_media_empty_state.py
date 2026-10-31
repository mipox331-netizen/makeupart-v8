from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


REQUIRED_MEDIA_COLUMNS = {
    ("beauty_jobs", "before_image_url"),
    ("beauty_jobs", "after_image_url"),
    ("beauty_jobs", "input_file_path"),
    ("beauty_jobs", "output_file_path"),
    ("beauty_results", "before_image_url"),
    ("beauty_results", "after_image_url"),
    ("watermarks", "logo_url"),
}


class MediaInventoryError(RuntimeError):
    pass


def verify_empty_media_inventory(manifest_path: Path) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MediaInventoryError("Private media backup manifest cannot be read.") from exc

    if manifest.get("format") not in {
        "makeupart-supabase-storage-media-backup-v1",
        "makeupart-google-drive-media-backup-v1",
    }:
        raise MediaInventoryError("Private media backup manifest format is not supported.")

    rows = manifest.get("files")
    file_count = manifest.get("file_count")
    total_bytes = manifest.get("total_bytes")
    if not isinstance(rows, list) or not isinstance(file_count, int) or not isinstance(total_bytes, int):
        raise MediaInventoryError("Private media backup manifest totals are invalid.")
    if file_count != len(rows):
        raise MediaInventoryError("Private media backup manifest file count is inconsistent.")
    if file_count > 0:
        return file_count
    if total_bytes != 0 or rows:
        raise MediaInventoryError("An empty private media inventory must have zero bytes and no file entries.")

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise MediaInventoryError(
            "The production PostgreSQL database URL is required to verify an empty private media store."
        )
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg2://" + database_url[len("postgres://"):]

    engine = None
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 15, "sslmode": "require"},
        )
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).scalar_one()
            if revision != "0014_beauty_media_paths":
                raise MediaInventoryError(
                    "The database is not at the current media schema migration head."
                )

            columns = connection.execute(text("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name = ANY(:tables)
            """), {"tables": ["beauty_jobs", "beauty_results", "watermarks"]}).all()
            existing = {(row[0], row[1]) for row in columns}
            missing = sorted(REQUIRED_MEDIA_COLUMNS - existing)
            if missing:
                raise MediaInventoryError(
                    "Cannot verify an empty private media store because expected media-reference columns are missing."
                )

            reference_count = connection.execute(text("""
                SELECT
                  (SELECT count(*) FROM public.beauty_jobs WHERE before_image_url IS NOT NULL)
                + (SELECT count(*) FROM public.beauty_jobs WHERE after_image_url IS NOT NULL)
                + (SELECT count(*) FROM public.beauty_jobs WHERE input_file_path IS NOT NULL)
                + (SELECT count(*) FROM public.beauty_jobs WHERE output_file_path IS NOT NULL)
                + (SELECT count(*) FROM public.beauty_results WHERE before_image_url IS NOT NULL)
                + (SELECT count(*) FROM public.beauty_results WHERE after_image_url IS NOT NULL)
                + (SELECT count(*) FROM public.watermarks WHERE logo_url IS NOT NULL)
            """)).scalar_one()
    except MediaInventoryError:
        raise
    except Exception as exc:
        raise MediaInventoryError(
            "The production database could not verify empty media references; refusing an empty backup."
        ) from exc
    finally:
        if engine is not None:
            engine.dispose()

    if int(reference_count or 0) > 0:
        raise MediaInventoryError(
            "Google Drive contains no media but the database still references customer photos or salon logos; restore the source media before accepting an empty backup."
        )

    print(
        "Verified empty-state backup: no beauty jobs, result images or salon-logo references "
        "point to missing Google Drive media. No customer image data is missing from the empty Drive store."
    )
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_supabase_media_empty_state.py MANIFEST_PATH")
    try:
        count = verify_empty_media_inventory(Path(sys.argv[1]))
    except MediaInventoryError as exc:
        raise SystemExit(str(exc)) from None
    if count:
        print(f"Google Drive private media inventory contains {count} object(s); encrypted backup can proceed.")


if __name__ == "__main__":
    main()
