from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_RELEASE_ASSET_BYTES = 2 * 1024 * 1024 * 1024 - 1
ALLOWED_CATEGORIES = {"database", "media"}
RUN_ID_RE = re.compile(r"^[0-9]+-a[0-9]+$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class BackupStorageError(RuntimeError):
    """A private GitHub Releases backup operation failed safely."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise BackupStorageError(f"Missing required setting: {name}.")
    return value


def _backup_repository() -> str:
    repository = _required_env("BACKUP_REPOSITORY")
    if not REPOSITORY_RE.fullmatch(repository):
        raise BackupStorageError("BACKUP_REPOSITORY must use owner/repository format.")
    source_repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if source_repository and repository.lower() == source_repository.lower():
        raise BackupStorageError("Backup repository must be separate from the application repository.")
    _required_env("GH_TOKEN")
    return repository


def _gh(*args: str) -> str:
    token = _required_env("GH_TOKEN")
    repository = _backup_repository()
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    try:
        result = subprocess.run(
            ["gh", *args, "--repo", repository],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
    except FileNotFoundError:
        raise BackupStorageError("GitHub CLI is unavailable on this runner.") from None
    except subprocess.TimeoutExpired:
        raise BackupStorageError("GitHub Releases operation timed out.") from None
    if result.returncode != 0:
        # Do not echo CLI output; it may contain private repository or request metadata.
        raise BackupStorageError(
            f"GitHub Releases operation failed (exit {result.returncode}); "
            "check the private backup repository and token permissions."
        )
    return result.stdout


def _validate_category_run(category: str, run_id: str) -> None:
    if category not in ALLOWED_CATEGORIES:
        raise BackupStorageError("Backup category must be database or media.")
    if not RUN_ID_RE.fullmatch(run_id):
        raise BackupStorageError("GitHub workflow run identifier is invalid.")


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _verify_local_archive(archive: Path, checksum_file: Path) -> tuple[int, str]:
    if not archive.is_file() or not checksum_file.is_file():
        raise BackupStorageError("Encrypted archive or checksum sidecar is missing.")
    size, digest = _sha256(archive)
    if size <= 0 or size > MAX_RELEASE_ASSET_BYTES:
        raise BackupStorageError("Encrypted archive must be non-empty and smaller than GitHub's 2 GiB asset limit.")
    sidecar_text = checksum_file.read_text(encoding="utf-8").strip()
    expected = sidecar_text.split(maxsplit=1)[0] if sidecar_text else ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected) or expected.lower() != digest:
        raise BackupStorageError("Encrypted archive SHA-256 does not match its checksum sidecar.")
    return size, digest


def _ensure_private_target(repository: str) -> None:
    status = _gh("repo", "view", "--json", "isPrivate", "--jq", ".isPrivate").strip()
    if status != "true":
        raise BackupStorageError("Backup repository must be private. No backup asset was uploaded.")


def _prune_expired(category: str, retention_days: int) -> int:
    if retention_days < 1 or retention_days > 90:
        raise BackupStorageError("BACKUP_RETENTION_DAYS must be between 1 and 90.")
    raw = _gh("release", "list", "--limit", "1000", "--json", "tagName,createdAt")
    try:
        releases = json.loads(raw or "[]")
    except json.JSONDecodeError:
        raise BackupStorageError("GitHub Releases returned an invalid retention listing.") from None

    prefix = f"makeupart-{category}-"
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for release in releases:
        tag = str(release.get("tagName") or "")
        created_at = str(release.get("createdAt") or "")
        if not tag.startswith(prefix):
            continue
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created < cutoff:
            _gh("release", "delete", tag, "--yes", "--cleanup-tag")
            removed += 1
    return removed


def upload(category: str, archive: Path, checksum_file: Path, run_id: str) -> str:
    _validate_category_run(category, run_id)
    repository = _backup_repository()
    archive_size, archive_sha = _verify_local_archive(archive, checksum_file)
    _ensure_private_target(repository)

    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "14"))
    removed = _prune_expired(category, retention_days)
    tag = f"makeupart-{category}-{run_id}"
    title = f"MakeupArt encrypted {category} backup"
    notes = (
        "Client-side GPG AES-256 encrypted backup. "
        "No plaintext customer data is stored in this release."
    )
    _gh(
        "release",
        "create",
        tag,
        "--title",
        title,
        "--notes",
        notes,
        "--prerelease",
        str(archive),
        str(checksum_file),
    )

    try:
        with tempfile.TemporaryDirectory(prefix="makeupart-release-verify-") as temp_dir:
            _gh("release", "download", tag, "--dir", temp_dir)
            downloaded_archive = Path(temp_dir) / archive.name
            downloaded_checksum = Path(temp_dir) / checksum_file.name
            if not downloaded_archive.is_file() or not downloaded_checksum.is_file():
                raise BackupStorageError("Uploaded GitHub Release is missing the encrypted archive or checksum asset.")
            verified_size, verified_sha = _verify_local_archive(downloaded_archive, downloaded_checksum)
            if verified_size != archive_size or verified_sha != archive_sha:
                raise BackupStorageError("GitHub Release download verification did not match the uploaded archive.")
    except BackupStorageError:
        raise
    except Exception:
        raise BackupStorageError("GitHub Release upload verification failed.") from None

    print(
        f"Encrypted {category} backup uploaded to a private GitHub repository and verified: "
        f"bytes={archive_size}, expired_releases_removed={removed}, retention_days={retention_days}."
    )
    return tag


def download(category: str, run_id: str, destination: Path) -> Path:
    _validate_category_run(category, run_id)
    _backup_repository()
    tag = f"makeupart-{category}-{run_id}"
    destination.mkdir(parents=True, exist_ok=True)
    _gh("release", "download", tag, "--dir", str(destination))

    if category == "database":
        pattern = "*.dump.gpg"
    else:
        pattern = "*.tar.gz.gpg"
    archives = sorted(destination.glob(pattern))
    if len(archives) != 1:
        raise BackupStorageError("Private GitHub Release must contain exactly one encrypted archive.")
    archive_path = archives[0]
    checksum_path = Path(str(archive_path) + ".sha256")
    try:
        _verify_local_archive(archive_path, checksum_path)
    except BackupStorageError:
        archive_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        raise
    print(
        f"Encrypted {category} backup downloaded from the private GitHub repository "
        "and SHA-256 verified. Production data was not changed."
    )
    return archive_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: github_release_backup.py upload CATEGORY ARCHIVE CHECKSUM_FILE RUN_ID "
            "or download CATEGORY RUN_ID DESTINATION_DIR"
        )
    try:
        command = sys.argv[1]
        if command == "upload" and len(sys.argv) == 6:
            upload(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5])
        elif command == "download" and len(sys.argv) == 5:
            download(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        else:
            raise BackupStorageError("Invalid GitHub Release backup command or arguments.")
    except BackupStorageError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        raise SystemExit(
            f"GitHub Release backup operation failed ({type(exc).__name__}); "
            "private repository details and credentials were withheld."
        ) from None


if __name__ == "__main__":
    main()
