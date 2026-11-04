"""Create a checksum manifest for media downloaded from the production Modal Volume.

The GitHub backup workflow downloads the mounted production Volume first, then
uses this manifest to encrypt and upload that exact snapshot to Google Drive.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 3 * 1024 * 1024 * 1024
MAX_FILES = 10_000


class MediaManifestError(RuntimeError):
    """The Modal Volume contains data that cannot be safely snapshotted."""


def _hash_stable_file(path: Path) -> tuple[int, str]:
    """Hash one regular file without following symlinks or accepting live mutation."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MediaManifestError("A Modal media file could not be opened safely.") from exc

    digest = hashlib.sha256()
    size = 0
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MediaManifestError("Modal media backup accepts regular files only.")
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise MediaManifestError("A media file exceeds the 512 MiB backup limit.")
                digest.update(block)
        after = os.fstat(descriptor)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or size != after.st_size:
            raise MediaManifestError("A media file changed while its backup checksum was being calculated.")
    finally:
        os.close(descriptor)

    if size == 0:
        raise MediaManifestError("An empty media object was found; refusing an incomplete backup.")
    return size, digest.hexdigest()


def build_manifest(media_root: Path, manifest_path: Path) -> tuple[int, int]:
    """Write a deterministic, privacy-safe inventory of a downloaded Modal Volume."""
    root = media_root.expanduser().resolve()
    if not root.is_dir():
        raise MediaManifestError("The downloaded Modal media directory is missing.")

    entries: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    total_bytes = 0

    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink():
            raise MediaManifestError("Symbolic links are not allowed in the Modal media backup.")
        if candidate.is_dir():
            continue
        if not candidate.exists() or not candidate.is_file():
            raise MediaManifestError("The Modal media Volume contains an unsupported filesystem entry.")

        relative = candidate.relative_to(root).as_posix()
        safe = PurePosixPath(relative)
        if (
            not relative
            or safe.is_absolute()
            or safe.as_posix() != relative
            or "\\" in relative
            or any(part in ("", ".", "..") for part in safe.parts)
        ):
            raise MediaManifestError("The Modal media Volume contains an unsafe relative path.")
        if relative in seen_paths:
            raise MediaManifestError("Duplicate Modal media paths were found.")
        seen_paths.add(relative)

        if len(entries) >= MAX_FILES:
            raise MediaManifestError("Modal media inventory exceeds the 10,000-file backup limit.")
        size, digest = _hash_stable_file(candidate)
        if total_bytes + size > MAX_TOTAL_BYTES:
            raise MediaManifestError("Modal media exceeds the 3 GiB encrypted backup limit.")
        total_bytes += size
        entries.append({"path": relative, "size": size, "sha256": digest})

    entries.sort(key=lambda row: str(row["path"]))
    manifest = {
        "format": "makeupart-modal-volume-media-backup-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest_path.with_name(manifest_path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(manifest, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, manifest_path)
    finally:
        temporary.unlink(missing_ok=True)

    print(
        f"Production Modal Volume inventory captured: files={len(entries)}, bytes={total_bytes}. "
        "Customer paths, account IDs and image contents were not logged."
    )
    return len(entries), total_bytes


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: modal_volume_media_manifest.py MEDIA_DIR MANIFEST_PATH")
    try:
        build_manifest(Path(sys.argv[1]), Path(sys.argv[2]))
    except MediaManifestError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
