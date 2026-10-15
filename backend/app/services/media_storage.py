"""Private persistent media mirror for the MakeupArt Supabase project."""
from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings

EXPECTED_SUPABASE_URL = "https://riakbjcxcaqjaqagncmu.supabase.co"


class MediaStorageError(RuntimeError):
    """Media could not be safely persisted or restored."""


def is_configured() -> bool:
    return bool(settings.SUPABASE_SERVICE_ROLE_KEY.strip())


def _config():
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    configured_url = settings.SUPABASE_URL.strip().rstrip("/")
    if not key and not configured_url:
        if settings.REQUIRE_DURABLE_MEDIA:
            raise MediaStorageError("Durable media storage is required but is not configured.")
        return None
    if not key or configured_url != EXPECTED_SUPABASE_URL:
        raise MediaStorageError("Durable media storage configuration is incomplete or invalid.")
    bucket = settings.SUPABASE_STORAGE_BUCKET.strip()
    if not bucket or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in bucket):
        raise MediaStorageError("Durable media bucket configuration is invalid.")
    return EXPECTED_SUPABASE_URL, key, bucket


def _key(path: str | Path) -> str:
    root = settings.media_root_path.resolve()
    candidate = Path(path).expanduser().resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise MediaStorageError("Media path is outside its configured storage root.") from exc
    key = relative.as_posix()
    if not key or key == "." or ".." in key.split("/"):
        raise MediaStorageError("Media path is invalid.")
    return key


def _url(bucket: str, key: str) -> str:
    escaped_bucket = quote(bucket, safe="")
    escaped_path = "/".join(quote(piece, safe="") for piece in key.split("/"))
    return f"{EXPECTED_SUPABASE_URL}/storage/v1/object/{escaped_bucket}/{escaped_path}"


def _headers(key: str, content_type: str | None = None) -> dict[str, str]:
    result = {"apikey": key, "Authorization": f"Bearer {key}"}
    if content_type:
        result["Content-Type"] = content_type
    return result


def persist_media_file(path: str | Path) -> bool:
    """Upload a local media file to its matching private-bucket key."""
    candidate = Path(path).expanduser().resolve()
    object_key = _key(candidate)
    config = _config()
    if config is None:
        return False
    _, service_key, bucket = config
    if not candidate.is_file():
        raise MediaStorageError("Media file is missing before persistent upload.")
    media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    try:
        with candidate.open("rb") as stream:
            response = httpx.post(
                _url(bucket, object_key),
                headers={**_headers(service_key, media_type), "x-upsert": "true"},
                content=stream,
                timeout=httpx.Timeout(45.0, connect=10.0),
            )
    except httpx.HTTPError as exc:
        raise MediaStorageError("Persistent media storage could not be reached.") from exc
    if response.status_code not in (200, 201):
        raise MediaStorageError(f"Persistent media upload failed (HTTP {response.status_code}).")
    return True


def ensure_local_file(path: str | Path) -> bool:
    """Hydrate an authorized, salon-scoped file from its private object key."""
    candidate = Path(path).expanduser().resolve()
    object_key = _key(candidate)
    if candidate.is_file():
        return True
    config = _config()
    if config is None:
        return False
    _, service_key, bucket = config
    try:
        response = httpx.get(
            _url(bucket, object_key),
            headers=_headers(service_key),
            timeout=httpx.Timeout(45.0, connect=10.0),
        )
    except httpx.HTTPError as exc:
        raise MediaStorageError("Persistent media storage could not be reached.") from exc
    if response.status_code == 404:
        return False
    if response.status_code != 200:
        raise MediaStorageError(f"Persistent media download failed (HTTP {response.status_code}).")
    if len(response.content) > max(int(settings.MAX_UPLOAD_BYTES), 30 * 1024 * 1024):
        raise MediaStorageError("Persistent media object exceeds the safe download limit.")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    temporary = candidate.with_name(f".{candidate.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(response.content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, candidate)
    except OSError as exc:
        raise MediaStorageError("Persistent media could not be restored locally.") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return True
