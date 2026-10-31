from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ROOT_KEY = "makeupart_backup_root"
ROOT_VALUE = "v1"
RUN_KEY = "makeupart_backup_run_id"


def oauth_error_code(response):
    try:
        payload = response.json()
    except ValueError:
        return "unknown"
    candidate = payload.get("error") if isinstance(payload, dict) else None
    if candidate == "invalid_grant":
        return "invalid_grant"
    if (
        isinstance(candidate, str)
        and candidate.isascii()
        and 0 < len(candidate) <= 64
        and candidate.replace("_", "").replace("-", "").isalnum()
    ):
        return candidate
    return "unknown"


def abort(message: str) -> None:
    raise SystemExit(message)


def required_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    abort("Missing required Google Drive OAuth environment setting: " + " or ".join(names))
    raise AssertionError("unreachable")


def checked_json(response: requests.Response, description: str) -> dict:
    if response.status_code >= 400:
        abort(f"{description} failed (HTTP {response.status_code}); response body withheld.")
    try:
        payload = response.json()
    except ValueError:
        abort(f"{description} returned invalid JSON.")
    if not isinstance(payload, dict):
        abort(f"{description} returned an invalid response.")
    return payload


def checksum(path: Path) -> tuple[int, str]:
    digest = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def main() -> None:
    if len(sys.argv) != 4:
        abort("Usage: google_drive_backup_upload.py ARCHIVE CHECKSUM_FILE RUN_ID")
    archive = Path(sys.argv[1]).resolve()
    checksum_file = Path(sys.argv[2]).resolve()
    run_id = sys.argv[3]
    import re
    if not re.fullmatch(r"[0-9]+-a[0-9]+", run_id):
        abort("GitHub workflow run/attempt identifier is invalid.")
    if not archive.is_file() or not checksum_file.is_file():
        abort("Encrypted backup archive or checksum sidecar is missing.")

    client_id = required_env("GOOGLE_DRIVE_CLIENT_ID", "GDRIVE_CLIENT_ID")
    client_secret = required_env("GOOGLE_DRIVE_CLIENT_SECRET", "GDRIVE_CLIENT_SECRET")
    refresh_token = required_env("GOOGLE_DRIVE_REFRESH_TOKEN", "GDRIVE_REFRESH_TOKEN")

    with requests.Session() as session:
        try:
            token_response = session.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=(10, 30),
            )
        except requests.RequestException:
            abort("Google Drive OAuth token refresh could not reach Google.")
        if token_response.status_code != 200:
            error_code = oauth_error_code(token_response)
            if error_code == "invalid_grant":
                abort("Google Drive refresh token is expired or revoked (invalid_grant). When OAuth consent is External/Testing, publish the app to In production and authorize again with offline access; then replace GOOGLE_DRIVE_REFRESH_TOKEN.")
            abort(f"Google Drive OAuth token refresh failed (HTTP {token_response.status_code}, error={error_code}).")
        token_body = checked_json(token_response, "Google Drive OAuth token refresh")
        token = token_body.get("access_token")
        if token_response.status_code != 200 or not isinstance(token, str) or not token:
            abort("Google Drive OAuth token refresh did not return an access token.")
        headers = {"Authorization": "Bearer " + token}

        query = (
            "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
            f"and appProperties has {{ key='{ROOT_KEY}' and value='{ROOT_VALUE}' }}"
        )
        try:
            response = session.get(
                API + "/files",
                headers=headers,
                params={"q": query, "pageSize": 2, "fields": "files(id,mimeType)"},
                timeout=(10, 30),
            )
        except requests.RequestException:
            abort("Google Drive backup-folder lookup could not reach Google.")
        roots = checked_json(response, "Google Drive backup-folder lookup").get("files", [])
        if response.status_code != 200 or not isinstance(roots, list) or len(roots) > 1:
            abort("Google Drive returned an ambiguous backup-folder inventory.")
        if roots:
            folder_id = str(roots[0].get("id") or "")
        else:
            try:
                response = session.post(
                    API + "/files",
                    headers=headers,
                    params={"fields": "id,name,mimeType", "ignoreDefaultVisibility": "true"},
                    json={
                        "name": "MakeUpArt V8 Encrypted Backups",
                        "mimeType": "application/vnd.google-apps.folder",
                        "appProperties": {ROOT_KEY: ROOT_VALUE},
                    },
                    timeout=(10, 30),
                )
            except requests.RequestException:
                abort("Google Drive backup folder could not be created.")
            folder_id = str(checked_json(response, "Google Drive backup-folder creation").get("id") or "")
        if not folder_id:
            abort("Google Drive did not return a valid backup-folder ID.")

        for source in (archive, checksum_file):
            size, md5 = checksum(source)
            target_name = f"run-{run_id}-{source.name}"
            query = (
                f"'{folder_id}' in parents and trashed = false and "
                f"name = '{target_name.replace(chr(39), chr(92) + chr(39))}'"
            )
            try:
                existing_response = session.get(
                    API + "/files",
                    headers=headers,
                    params={"q": query, "pageSize": 2, "fields": "files(id,size,md5Checksum)"},
                    timeout=(10, 30),
                )
            except requests.RequestException:
                abort("Google Drive could not verify an existing backup object.")
            existing = checked_json(existing_response, "Google Drive backup-object lookup").get("files", [])
            if not isinstance(existing, list) or len(existing) > 1:
                abort("Duplicate Google Drive backup objects were found; refusing an ambiguous overwrite.")
            if existing:
                if int(existing[0].get("size") or -1) != size or str(existing[0].get("md5Checksum") or "").lower() != md5:
                    abort("A different backup object already exists for this workflow run; refusing overwrite.")
                print(f"Encrypted backup already exists in private Google Drive: {source.name}.")
                continue

            mime_type = "application/octet-stream"
            metadata = {
                "name": target_name,
                "mimeType": mime_type,
                "parents": [folder_id],
                "appProperties": {RUN_KEY: run_id, "makeupart_backup": "v1"},
            }
            try:
                start = session.post(
                    UPLOAD_API + "/files",
                    headers={
                        **headers,
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Type": mime_type,
                        "X-Upload-Content-Length": str(size),
                    },
                    params={"uploadType": "resumable", "fields": "id,name,size,md5Checksum"},
                    json=metadata,
                    timeout=(10, 30),
                )
            except requests.RequestException:
                abort("Google Drive could not start the encrypted backup upload.")
            if start.status_code not in (200, 201):
                abort(f"Google Drive rejected the encrypted backup upload setup (HTTP {start.status_code}).")
            session_url = start.headers.get("Location", "")
            from urllib.parse import urlsplit
            parsed = urlsplit(session_url)
            if parsed.scheme != "https" or not parsed.hostname or not (
                parsed.hostname == "googleapis.com" or parsed.hostname.endswith(".googleapis.com")
            ):
                abort("Google Drive returned an unsafe resumable upload URL.")
            try:
                with source.open("rb") as stream:
                    uploaded_response = session.put(
                        session_url,
                        data=stream,
                        headers={"Content-Type": mime_type, "Content-Length": str(size)},
                        timeout=(30, 900),
                    )
            except requests.RequestException:
                abort("Encrypted backup upload to Google Drive failed.")
            uploaded = checked_json(uploaded_response, "Google Drive encrypted backup upload")
            if uploaded_response.status_code not in (200, 201):
                abort("Google Drive did not confirm the encrypted backup upload.")
            if int(uploaded.get("size") or -1) != size or str(uploaded.get("md5Checksum") or "").lower() != md5:
                abort("Google Drive encrypted backup size or checksum verification failed.")
            print(f"Encrypted backup stored and checksum-verified in private Google Drive: {source.name} ({size} bytes).")

    print("Encrypted media backup copy is present in Google Drive. No plaintext customer media was uploaded.")


if __name__ == "__main__":
    main()
