from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.config import Config

PREFIX = "makeupart-backups"
MAX_STORED_BYTES = 9_500_000_000
ALLOWED_CATEGORIES = {"database", "media"}
RUN_ID_RE = re.compile(r"^[0-9]+-a[0-9]+$")


class BackupStorageError(RuntimeError):
    """A private Cloudflare R2 backup operation failed safely."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise BackupStorageError(f"Missing required R2 setting: {name}.")
    return value


def _bucket() -> str:
    return _required_env("R2_BUCKET_NAME")


def _client():
    account_id = _required_env("R2_ACCOUNT_ID")
    endpoint = os.environ.get(
        "R2_ENDPOINT_URL",
        f"https://{account_id}.r2.cloudflarestorage.com",
    ).strip()
    if not endpoint.startswith("https://"):
        raise BackupStorageError("R2_ENDPOINT_URL must use HTTPS.")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=_required_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
            s3={"addressing_style": "path"},
        ),
    )


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


def _objects(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            if isinstance(item, dict) and item.get("Key"):
                yield item


def _prune_expired(client, bucket: str, category: str, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    prefix = f"{PREFIX}/{category}/"
    for item in _objects(client, bucket, prefix):
        modified = item.get("LastModified")
        if modified is not None and modified < cutoff:
            client.delete_object(Bucket=bucket, Key=item["Key"])
            removed += 1
    return removed


def _ensure_free_quota(client, bucket: str, additional_bytes: int) -> int:
    current_bytes = sum(
        int(item.get("Size") or 0)
        for item in _objects(client, bucket, f"{PREFIX}/")
    )
    if current_bytes + additional_bytes > MAX_STORED_BYTES:
        raise BackupStorageError(
            "MakeupArt backups would exceed the 9.5 GB safety ceiling for the R2 free allowance. "
            "No new archive was uploaded; reduce retained backups or storage usage."
        )
    return current_bytes


def upload(category: str, archive: Path, checksum_file: Path, run_id: str) -> tuple[str, str]:
    _validate_category_run(category, run_id)
    if not archive.is_file() or not checksum_file.is_file():
        raise BackupStorageError("Encrypted archive or checksum sidecar is missing.")

    archive_size, archive_sha = _sha256(archive)
    sidecar_text = checksum_file.read_text(encoding="utf-8").strip()
    sidecar_hash = sidecar_text.split(maxsplit=1)[0] if sidecar_text else ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sidecar_hash) or sidecar_hash.lower() != archive_sha:
        raise BackupStorageError("Encrypted archive SHA-256 does not match its checksum sidecar.")

    sidecar_size, sidecar_sha = _sha256(checksum_file)
    bucket = _bucket()
    client = _client()
    retention_days = int(os.environ.get("R2_BACKUP_RETENTION_DAYS", "14"))
    if retention_days < 1 or retention_days > 90:
        raise BackupStorageError("R2_BACKUP_RETENTION_DAYS must be between 1 and 90.")

    for backup_category in sorted(ALLOWED_CATEGORIES):
        _prune_expired(client, bucket, backup_category, retention_days)
    _ensure_free_quota(client, bucket, archive_size + sidecar_size)

    base = f"{PREFIX}/{category}/{run_id}/"
    archive_key = base + archive.name
    checksum_key = archive_key + ".sha256"

    # The archive is already encrypted locally with GPG/AES-256 before this upload.
    client.upload_file(
        str(archive),
        bucket,
        archive_key,
        ExtraArgs={
            "ContentType": "application/octet-stream",
            "Metadata": {
                "sha256": archive_sha,
                "run-id": run_id,
                "category": category,
                "encryption": "client-side-gpg-aes256",
            },
        },
    )
    with checksum_file.open("rb") as body:
        client.put_object(
            Bucket=bucket,
            Key=checksum_key,
            Body=body,
            ContentLength=sidecar_size,
            ContentType="text/plain",
            Metadata={"sha256": sidecar_sha, "run-id": run_id, "category": category},
        )

    archive_head = client.head_object(Bucket=bucket, Key=archive_key)
    checksum_head = client.head_object(Bucket=bucket, Key=checksum_key)
    if (
        int(archive_head.get("ContentLength", -1)) != archive_size
        or str((archive_head.get("Metadata") or {}).get("sha256", "")).lower() != archive_sha
        or int(checksum_head.get("ContentLength", -1)) != sidecar_size
        or str((checksum_head.get("Metadata") or {}).get("sha256", "")).lower() != sidecar_sha
    ):
        raise BackupStorageError("Cloudflare R2 upload verification failed; archive was not accepted.")

    used = _ensure_free_quota(client, bucket, 0)
    print(
        f"Encrypted {category} backup uploaded and verified in private Cloudflare R2: "
        f"bytes={archive_size}, retained_storage_bytes={used}, retention_days={retention_days}."
    )
    return archive_key, checksum_key


def download(category: str, run_id: str, destination: Path) -> Path:
    _validate_category_run(category, run_id)
    bucket = _bucket()
    client = _client()
    prefix = f"{PREFIX}/{category}/{run_id}/"
    keys = sorted(str(item["Key"]) for item in _objects(client, bucket, prefix))
    archives = [key for key in keys if key.endswith(".dump.gpg") or key.endswith(".tar.gz.gpg")]
    if len(archives) != 1:
        raise BackupStorageError(
            "R2 must contain exactly one encrypted archive for the selected successful backup run."
        )
    archive_key = archives[0]
    checksum_key = archive_key + ".sha256"
    if checksum_key not in keys:
        raise BackupStorageError("The encrypted R2 backup checksum sidecar is missing.")

    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / Path(archive_key).name
    checksum_path = destination / (Path(archive_key).name + ".sha256")
    client.download_file(bucket, archive_key, str(archive_path))
    client.download_file(bucket, checksum_key, str(checksum_path))

    _size, digest = _sha256(archive_path)
    sidecar = checksum_path.read_text(encoding="utf-8").strip()
    expected = sidecar.split(maxsplit=1)[0] if sidecar else ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected) or expected.lower() != digest:
        archive_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)
        raise BackupStorageError("Downloaded R2 archive failed SHA-256 verification.")
    print(
        f"Encrypted {category} backup downloaded from private Cloudflare R2 and SHA-256 verified. "
        "No plaintext archive contents were exposed."
    )
    return archive_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: r2_backup_storage.py upload CATEGORY ARCHIVE CHECKSUM_FILE RUN_ID "
            "or download CATEGORY RUN_ID DESTINATION_DIR"
        )
    try:
        command = sys.argv[1]
        if command == "upload" and len(sys.argv) == 6:
            upload(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5])
        elif command == "download" and len(sys.argv) == 5:
            download(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        else:
            raise BackupStorageError("Invalid R2 backup command or arguments.")
    except BackupStorageError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        # Provider exceptions can contain request metadata; never echo raw details.
        raise SystemExit(
            f"Cloudflare R2 backup operation failed ({type(exc).__name__}); "
            "provider response and credentials were withheld."
        ) from None


if __name__ == "__main__":
    main()
