"""Private Google Drive media mirror for MakeUpArt V8.

Uses a user-owned Google Drive OAuth refresh token and the narrow drive.file scope.
Media is private: objects are never made public or served through share links.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

import httpx

from app.core.config import settings

_API = "https://www.googleapis.com/drive/v3"
_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_FOLDER_MIME = "application/vnd.google-apps.folder"
_ROOT_MARKER_KEY = "makeupart_root"
_ROOT_MARKER_VALUE = "v1"
_PATH_PROPERTY = "makeupart_path"
_MAX_RESTORE_BYTES = 512 * 1024 * 1024
_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: dict[str, object] = {}
_ROOT_LOCK = threading.Lock()
_ROOT_CACHE: dict[str, str] = {}


class GoogleDriveMediaError(RuntimeError):
    """Google Drive media could not be safely persisted, restored, or deleted."""


def is_configured() -> bool:
    return all(
        value.strip()
        for value in (
            settings.GOOGLE_DRIVE_CLIENT_ID,
            settings.GOOGLE_DRIVE_CLIENT_SECRET,
            settings.GOOGLE_DRIVE_REFRESH_TOKEN,
        )
    )


def _credentials() -> tuple[str, str, str] | None:
    values = (
        settings.GOOGLE_DRIVE_CLIENT_ID.strip(),
        settings.GOOGLE_DRIVE_CLIENT_SECRET.strip(),
        settings.GOOGLE_DRIVE_REFRESH_TOKEN.strip(),
    )
    if not any(values):
        # Production containers can have ephemeral local disks. Never silently
        # downgrade customer media to local-only storage in a live environment,
        # even if an old/missing env var leaves REQUIRE_DURABLE_MEDIA disabled.
        if settings.REQUIRE_DURABLE_MEDIA or settings.ENVIRONMENT.lower() == "production":
            raise GoogleDriveMediaError(
                "Durable media storage is required but Google Drive OAuth is not configured."
            )
        return None
    if not all(values):
        raise GoogleDriveMediaError(
            "Google Drive OAuth configuration is incomplete; set all required variables."
        )
    return values


def _relative_key(path: str | Path) -> str:
    root = settings.media_root_path.resolve()
    candidate = Path(path).expanduser().resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise GoogleDriveMediaError(
            "Media path is outside the configured media root."
        ) from exc
    key = relative.as_posix()
    if not key or key == "." or ".." in key.split("/"):
        raise GoogleDriveMediaError("Media path is invalid.")
    # Google Drive limits each appProperties key+value to 124 UTF-8 bytes.
    if len(key.encode("utf-8")) > 105:
        raise GoogleDriveMediaError("Media path is too long for the private storage index.")
    return key


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    timeout: float | httpx.Timeout = 30.0,
    **kwargs,
) -> httpx.Response:
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise GoogleDriveMediaError("Google Drive could not be reached.") from exc
    if response.status_code >= 400:
        raise GoogleDriveMediaError(
            f"Google Drive request failed (HTTP {response.status_code})."
        )
    return response


def _access_token() -> str:
    credentials = _credentials()
    if credentials is None:
        raise GoogleDriveMediaError("Google Drive OAuth is not configured.")
    client_id, client_secret, refresh_token = credentials
    cache_key = hashlib.sha256(
        (client_id + "\0" + client_secret + "\0" + refresh_token).encode("utf-8")
    ).hexdigest()
    now = time.monotonic()
    with _TOKEN_LOCK:
        if (
            _TOKEN_CACHE.get("key") == cache_key
            and isinstance(_TOKEN_CACHE.get("token"), str)
            and float(_TOKEN_CACHE.get("expires_at", 0)) > now
        ):
            return str(_TOKEN_CACHE["token"])
        try:
            response = httpx.post(
                _TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise GoogleDriveMediaError("Google Drive OAuth token refresh failed.") from exc
        if response.status_code != 200:
            raise GoogleDriveMediaError(
                f"Google Drive OAuth token refresh failed (HTTP {response.status_code})."
            )
        try:
            body = response.json()
            token = str(body["access_token"])
            lifetime = max(60, int(body.get("expires_in", 3600)))
        except (ValueError, KeyError, TypeError) as exc:
            raise GoogleDriveMediaError("Google Drive returned an invalid OAuth response.") from exc
        _TOKEN_CACHE.clear()
        _TOKEN_CACHE.update(
            key=cache_key,
            token=token,
            expires_at=now + lifetime - 60,
        )
        return token


def _root_folder_id(token: str) -> str:
    credentials = _credentials()
    if credentials is None:
        raise GoogleDriveMediaError("Google Drive OAuth is not configured.")
    cache_key = hashlib.sha256(
        (credentials[0] + "\\0" + credentials[2]).encode("utf-8")
    ).hexdigest()
    with _ROOT_LOCK:
        cached = _ROOT_CACHE.get(cache_key)
        if cached:
            return cached

        query = (
            "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
            "and appProperties has { key='makeupart_root' and value='v1' }"
        )
        response = _request(
            "GET",
            f"{_API}/files",
            token=token,
            params={"q": query, "pageSize": 1, "fields": "files(id,name,mimeType)"},
        )
        folders = response.json().get("files", [])
        if folders:
            folder_id = str(folders[0]["id"])
        else:
            response = _request(
                "POST",
                f"{_API}/files",
                token=token,
                json={
                    "name": "MakeUpArt V8 Private Media",
                    "mimeType": _FOLDER_MIME,
                    "appProperties": {
                        _ROOT_MARKER_KEY: _ROOT_MARKER_VALUE,
                    },
                },
                params={
                    "fields": "id,name,mimeType",
                    "ignoreDefaultVisibility": "true",
                },
            )
            folder_id = str(response.json().get("id", ""))
            if not folder_id:
                raise GoogleDriveMediaError("Google Drive did not return a media folder ID.")
        _ROOT_CACHE[cache_key] = folder_id
        return folder_id


def _escaped_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def verify_connection() -> None:
    """Verify OAuth access and ensure the app's private root folder is reachable."""
    token = _access_token()
    _root_folder_id(token)


def _find_media_object(path_key: str, token: str, folder_id: str) -> dict | None:
    escaped_key = _escaped_query_value(path_key)
    query = (
        f"'{folder_id}' in parents and trashed = false and "
        f"appProperties has {{ key='{_PATH_PROPERTY}' and value='{escaped_key}' }}"
    )
    response = _request(
        "GET",
        f"{_API}/files",
        token=token,
        params={
            "q": query,
            "pageSize": 2,
            "fields": "files(id,name,mimeType,size,md5Checksum)",
        },
    )
    files = response.json().get("files", [])
    if len(files) > 1:
        raise GoogleDriveMediaError(
            "Duplicate private media records were found; refusing ambiguous restoration."
        )
    return files[0] if files else None


def _read_chunks(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            yield chunk


def persist_media_file(path: str | Path) -> bool:
    """Upload or update one file in the private Drive folder. False means local-only mode."""
    credentials = _credentials()
    if credentials is None:
        return False

    candidate = Path(path).expanduser().resolve()
    path_key = _relative_key(candidate)
    if not candidate.is_file():
        raise GoogleDriveMediaError("Media file is missing before cloud persistence.")

    token = _access_token()
    folder_id = _root_folder_id(token)
    existing = _find_media_object(path_key, token, folder_id)
    digest = hashlib.sha256(path_key.encode("utf-8")).hexdigest()[:24]
    display_name = f"{digest}-{candidate.name}"
    media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    metadata = {
        "name": display_name,
        "mimeType": media_type,
        "appProperties": {_PATH_PROPERTY: path_key},
    }
    if existing:
        upload_url = f"{_UPLOAD_API}/files/{existing['id']}"
        method = "PATCH"
    else:
        metadata["parents"] = [folder_id]
        upload_url = f"{_UPLOAD_API}/files"
        method = "POST"

    upload_params = {
        "uploadType": "resumable",
        "fields": "id,name,size,md5Checksum",
    }
    if not existing:
        # Override Workspace defaults that automatically expose newly uploaded
        # files to a domain; parent-folder permissions still apply.
        upload_params["ignoreDefaultVisibility"] = "true"

    response = _request(
        method,
        upload_url,
        token=token,
        params=upload_params,
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": media_type,
            "X-Upload-Content-Length": str(candidate.stat().st_size),
        },
        json=metadata,
    )
    session_url = response.headers.get("Location")
    if not session_url:
        raise GoogleDriveMediaError("Google Drive did not return a resumable upload session.")
    parsed_session_url = urlsplit(session_url)
    if (
        parsed_session_url.scheme != "https"
        or not parsed_session_url.hostname
        or not (
            parsed_session_url.hostname == "googleapis.com"
            or parsed_session_url.hostname.endswith(".googleapis.com")
        )
    ):
        raise GoogleDriveMediaError(
            "Google Drive returned an unsafe resumable upload URL."
        )

    response = _request(
        "PUT",
        session_url,
        token=token,
        timeout=httpx.Timeout(180.0, connect=20.0),
        headers={
            "Content-Type": media_type,
            "Content-Length": str(candidate.stat().st_size),
        },
        content=_read_chunks(candidate),
    )
    if response.status_code not in (200, 201):
        raise GoogleDriveMediaError(
            f"Google Drive media upload failed (HTTP {response.status_code})."
        )

    # A 2xx response alone is not enough to prove the stored photo/logo matches
    # the source. Verify Google's final resumable-upload metadata before the
    # calling API commits database rows that reference this media object.
    try:
        uploaded = response.json()
        uploaded_size = int(uploaded.get("size", -1))
        uploaded_md5 = str(uploaded.get("md5Checksum") or "").strip().lower()
    except (ValueError, TypeError, AttributeError) as exc:
        raise GoogleDriveMediaError(
            "Google Drive returned invalid media-upload verification metadata."
        ) from exc

    expected_size = candidate.stat().st_size
    expected_md5 = hashlib.md5(usedforsecurity=False)
    for chunk in _read_chunks(candidate):
        expected_md5.update(chunk)
    if uploaded_size != expected_size:
        raise GoogleDriveMediaError(
            "Google Drive media upload size verification failed."
        )
    if not uploaded_md5 or uploaded_md5 != expected_md5.hexdigest().lower():
        raise GoogleDriveMediaError(
            "Google Drive media upload checksum verification failed."
        )
    return True


def ensure_local_file(path: str | Path) -> bool:
    """Restore a missing authorized local file from the private Drive folder."""
    candidate = Path(path).expanduser().resolve()
    path_key = _relative_key(candidate)
    if candidate.is_file():
        return True

    credentials = _credentials()
    if credentials is None:
        return False
    token = _access_token()
    folder_id = _root_folder_id(token)
    media = _find_media_object(path_key, token, folder_id)
    if media is None:
        return False

    candidate.parent.mkdir(parents=True, exist_ok=True)
    temporary = candidate.with_name(f".{candidate.name}.{uuid.uuid4().hex}.tmp")
    headers = {"Authorization": f"Bearer {token}"}
    total = 0
    # Drive exposes md5Checksum for binary files. Validate it before publishing a
    # restored photo so a truncated/corrupted download never replaces the local copy.
    expected_md5 = str(media.get("md5Checksum") or "").strip().lower()
    actual_md5 = hashlib.md5(usedforsecurity=False)
    try:
        with httpx.stream(
            "GET",
            f"{_API}/files/{media['id']}",
            params={"alt": "media"},
            headers=headers,
            timeout=httpx.Timeout(120.0, connect=20.0),
            follow_redirects=True,
        ) as response:
            if response.status_code == 404:
                return False
            if response.status_code != 200:
                raise GoogleDriveMediaError(
                    f"Google Drive media restore failed (HTTP {response.status_code})."
                )
            with temporary.open("wb") as destination:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    total += len(chunk)
                    if total > _MAX_RESTORE_BYTES:
                        raise GoogleDriveMediaError(
                            "Google Drive media object exceeds the safe restore limit."
                        )
                    actual_md5.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
        if total == 0:
            raise GoogleDriveMediaError("Google Drive returned an empty media object.")
        if expected_md5 and actual_md5.hexdigest().lower() != expected_md5:
            raise GoogleDriveMediaError(
                "Google Drive media checksum mismatch; refusing to restore a corrupted file."
            )
        os.replace(temporary, candidate)
        return True
    except GoogleDriveMediaError:
        raise
    except (httpx.HTTPError, OSError) as exc:
        raise GoogleDriveMediaError("Google Drive media could not be restored locally.") from exc
    finally:
        temporary.unlink(missing_ok=True)


def delete_media_file(path: str | Path) -> bool:
    """Permanently delete one matching private Drive object; false means local-only mode."""
    credentials = _credentials()
    if credentials is None:
        return False

    path_key = _relative_key(path)
    token = _access_token()
    folder_id = _root_folder_id(token)
    media = _find_media_object(path_key, token, folder_id)
    if media is None:
        return True

    # Privacy deletion must not merely move a client image into Drive Trash,
    # where the central account owner could still restore or view it.
    response = _request(
        "DELETE",
        f"{_API}/files/{media['id']}",
        token=token,
    )
    # Drive files.delete normally returns HTTP 204 with an empty body.
    # _request raises for HTTP errors, so no response body needs to be parsed.
    if response.status_code not in (200, 204):
        raise GoogleDriveMediaError(
            "Google Drive did not confirm permanent deletion of the matched private media object."
        )
    return True
