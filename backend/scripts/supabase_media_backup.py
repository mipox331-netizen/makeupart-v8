from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 3 * 1024 * 1024 * 1024
PAGE_SIZE = 1000


class BackupError(RuntimeError):
    pass


def _safe_request(
    session: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    timeout: tuple[int, int] = (10, 60),
    **kwargs,
) -> requests.Response:
    try:
        response = session.request(
            method,
            url,
            headers=headers,
            timeout=httpx.Timeout(timeout[1], connect=timeout[0]),
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise BackupError("Supabase Storage request could not be completed.") from exc
    provider_code = "unknown"
    provider_message = "no structured error details"
    if response.status_code >= 400:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                provider_code = str(
                    payload.get("code") or payload.get("error") or payload.get("statusCode") or "unknown"
                )[:80]
                provider_message = str(payload.get("message") or payload.get("error_description") or "")[:180]
        except ValueError:
            pass
        # Storage errors help distinguish invalid credentials from request
        # shape errors. Redact anything resembling tokens, credentials, URLs or
        # long opaque identifiers before writing diagnostics to Actions logs.
        import re

        provider_message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", provider_message)
        provider_message = re.sub(r"(?i)(sb_(?:secret|publishable)_[A-Za-z0-9_-]+)", "[REDACTED_KEY]", provider_message)
        provider_message = re.sub(r"[A-Za-z0-9_-]{40,}", "[REDACTED_TOKEN]", provider_message)
        provider_message = re.sub(r"https?://\S+", "[REDACTED_URL]", provider_message)
        provider_message = re.sub(r"[\r\n\t]+", " ", provider_message).strip()
        raise BackupError(
            f"Supabase Storage request failed (HTTP {response.status_code}, "
            f"code={provider_code}); provider message: {provider_message or 'not supplied'}."
        )
    return response


def _safe_relative_key(key: str) -> str:
    path = PurePosixPath(key)
    if (
        not key
        or path.is_absolute()
        or path.as_posix() != key
        or "\\" in key
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise BackupError("Supabase returned an unsafe private media object path.")
    return key


def backup_media(destination: Path, manifest_path: Path) -> tuple[int, int]:
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.environ.get("SUPABASE_MEDIA_BUCKET", "makeupart-media").strip()
    if not supabase_url:
        # Derive the project endpoint without embedding a project reference in source.
        # Direct DB hosts use <project-ref>.supabase.co; Supavisor usernames are
        # normally postgres.<project-ref>. If neither is available, require an
        # explicit SUPABASE_URL secret rather than guessing.
        from urllib.parse import unquote, urlsplit

        database_url = os.environ.get("SUPABASE_DB_URL", "").strip()
        parsed_database = urlsplit(database_url)
        host = (parsed_database.hostname or "").lower()
        project_ref = ""
        if host.endswith(".supabase.co"):
            project_ref = host.removesuffix(".supabase.co")
        elif parsed_database.username and "." in unquote(parsed_database.username):
            candidate = unquote(parsed_database.username).split(".", 1)[1]
            if candidate.replace("-", "").isalnum():
                project_ref = candidate
        if project_ref:
            supabase_url = f"https://{project_ref}.supabase.co"

    if not supabase_url or not service_key or not bucket or "/" in bucket:
        raise BackupError(
            "Supabase private-media backup configuration is incomplete; "
            "set SUPABASE_URL or a project-qualified SUPABASE_DB_URL."
        )
    if not supabase_url.startswith("https://"):
        raise BackupError("SUPABASE_URL must use HTTPS.")

    api = supabase_url + "/storage/v1"
    headers = {
        "apikey": service_key,
        "Authorization": "Bearer " + service_key,
        "Accept": "application/json",
    }
    session = httpx.Client(follow_redirects=True)

    # Ensure the source is the intended private bucket. Never back up a bucket
    # whose metadata says public=true.
    bucket_url = api + "/bucket/" + quote(bucket, safe="")
    try:
        bucket_response = _safe_request(session, "GET", bucket_url, headers=headers)
    except BackupError as exc:
        if "(HTTP 404)" not in str(exc) and "code=NoSuchBucket" not in str(exc):
            raise
        created = _safe_request(
            session,
            "POST",
            api + "/bucket",
            headers=headers,
            json={
                "id": bucket,
                "name": bucket,
                "public": False,
                "file_size_limit": MAX_FILE_BYTES,
                "allowed_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                    "application/octet-stream",
                ],
            },
        )
        try:
            bucket_info = created.json()
        except ValueError as parse_error:
            raise BackupError("Supabase returned invalid private bucket metadata.") from parse_error
    else:
        try:
            bucket_info = bucket_response.json()
        except ValueError as parse_error:
            raise BackupError("Supabase returned invalid private bucket metadata.") from parse_error
    if not isinstance(bucket_info, dict) or bucket_info.get("public") is not False:
        raise BackupError("MakeUpArt media bucket must be private.")

    destination.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    visited_prefixes: set[str] = set()
    total_bytes = 0

    def list_prefix(prefix: str, depth: int = 0) -> None:
        nonlocal total_bytes
        if depth > 20:
            raise BackupError("Supabase media directory nesting exceeds the safety limit.")
        normalized_prefix = prefix.strip("/")
        if normalized_prefix in visited_prefixes:
            return
        visited_prefixes.add(normalized_prefix)

        offset = 0
        while True:
            response = _safe_request(
                session,
                "POST",
                api + "/object/list/" + quote(bucket, safe=""),
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "prefix": normalized_prefix,
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                },
            )
            try:
                rows = response.json()
            except ValueError as parse_error:
                raise BackupError("Supabase returned invalid media inventory data.") from parse_error
            if not isinstance(rows, list):
                raise BackupError("Supabase returned an invalid media inventory page.")

            for row in rows:
                if not isinstance(row, dict):
                    raise BackupError("Supabase returned an invalid media inventory record.")
                name = str(row.get("name") or "").strip("/")
                if not name:
                    raise BackupError("Supabase returned an empty media object name.")
                if name.startswith(normalized_prefix + "/") and normalized_prefix:
                    key = name
                    basename = name[len(normalized_prefix) + 1 :]
                else:
                    key = (normalized_prefix + "/" if normalized_prefix else "") + name
                    basename = name

                # Folder entries have no object ID/metadata. Recurse by prefix;
                # object entries always retain their original tenant-scoped key.
                metadata = row.get("metadata")
                is_folder = row.get("id") is None or metadata is None
                if is_folder:
                    list_prefix(key, depth + 1)
                    continue

                key = _safe_relative_key(key)
                if key in seen_keys:
                    raise BackupError("Duplicate Supabase media object paths were found.")
                seen_keys.add(key)

                try:
                    expected_size = int(metadata.get("size") or 0)
                except (TypeError, ValueError, AttributeError) as size_error:
                    raise BackupError("Supabase returned invalid media object size metadata.") from size_error
                if expected_size > MAX_FILE_BYTES:
                    raise BackupError("A media object exceeds the 512 MiB restore limit.")
                if expected_size and total_bytes + expected_size > MAX_TOTAL_BYTES:
                    raise BackupError("Private media exceeds the 3 GiB encrypted backup limit.")

                object_url = (
                    api + "/object/" + quote(bucket, safe="") + "/" + quote(key, safe="/")
                )
                downloaded = _safe_request(
                    session,
                    "GET",
                    object_url,
                    headers=headers,
                    timeout=(10, 120),
                )
                content = downloaded.content
                size = len(content)
                if not size:
                    raise BackupError("An empty private media object was found; backup stopped.")
                if size > MAX_FILE_BYTES or total_bytes + size > MAX_TOTAL_BYTES:
                    raise BackupError("Private media exceeds the configured encrypted backup limits.")
                if expected_size and size != expected_size:
                    raise BackupError("Private media size verification failed.")

                output = destination.joinpath(*PurePosixPath(key).parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(content)
                digest = hashlib.sha256(content).hexdigest()
                entries.append({"path": key, "size": size, "sha256": digest})
                total_bytes += size

            offset += len(rows)
            if len(rows) < PAGE_SIZE:
                break

    list_prefix("")
    if not entries:
        raise BackupError(
            "The private media bucket is empty. Refusing to claim customer-photo backup success."
        )

    entries.sort(key=lambda item: str(item["path"]))
    manifest = {
        "format": "makeupart-supabase-storage-media-backup-v1",
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
    }
    manifest_path.write_text(
        json.dumps(manifest, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    return len(entries), total_bytes


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: supabase_media_backup.py MEDIA_DIR MANIFEST_PATH")
    try:
        count, total = backup_media(Path(sys.argv[1]), Path(sys.argv[2]))
    except BackupError as exc:
        raise SystemExit(str(exc)) from None
    print(
        f"Private Supabase media inventory captured: files={count}, bytes={total}. "
        "Object paths, IDs, tokens and image contents were not logged."
    )


if __name__ == "__main__":
    main()
