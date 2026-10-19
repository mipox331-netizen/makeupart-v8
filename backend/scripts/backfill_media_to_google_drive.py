"""Backfill existing local salon media into private Google Drive storage.

Run from the backend directory after configuring the three Google Drive OAuth values.
Preview first; the script uploads only when invoked with --apply.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.services import google_drive_media
from app.services.google_drive_media import GoogleDriveMediaError


def discover_media() -> list[Path]:
    root = settings.media_root_path / "salons"
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".tmp")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually upload local media to the private Google Drive folder.",
    )
    args = parser.parse_args()

    if not google_drive_media.is_configured():
        parser.error(
            "Google Drive OAuth is not configured. Set GOOGLE_DRIVE_CLIENT_ID, "
            "GOOGLE_DRIVE_CLIENT_SECRET, and GOOGLE_DRIVE_REFRESH_TOKEN first."
        )

    files = discover_media()
    print(f"Found {len(files)} local salon media file(s).")
    if not args.apply:
        print("Dry run only; rerun with --apply to upload these files. No files were changed.")
        return 0

    uploaded = 0
    failed = 0
    for path in files:
        try:
            if google_drive_media.persist_media_file(path):
                uploaded += 1
        except GoogleDriveMediaError:
            failed += 1
            # Avoid printing customer file paths in logs.
            print("A media upload failed; local file was retained. Check private Drive configuration/logs.")

    print(f"Backfill finished: uploaded={uploaded}, failed={failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
