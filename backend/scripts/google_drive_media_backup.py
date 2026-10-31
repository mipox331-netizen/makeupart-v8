import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import requests

API = "https://www.googleapis.com/drive/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 3 * 1024 * 1024 * 1024
session = requests.Session()

def oauth_error_code(response):
    try:
        payload = response.json()
    except ValueError:
        return "unknown"
    candidate = payload.get("error") if isinstance(payload, dict) else None
    if (
        isinstance(candidate, str)
        and candidate.isascii()
        and 0 < len(candidate) <= 64
        and candidate.replace("_", "").replace("-", "").isalnum()
    ):
        return candidate
    return "unknown"


def abort(message):
    raise SystemExit(message)

def checked_json(response, description):
    if response.status_code >= 400:
        abort(f"{description} failed (HTTP {response.status_code}); response body withheld.")
    try:
        return response.json()
    except ValueError:
        abort(f"{description} returned invalid JSON.")

try:
    token_response = session.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["GOOGLE_DRIVE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_DRIVE_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_DRIVE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=(10, 30),
    )
except requests.RequestException:
    abort("Google Drive OAuth token refresh could not reach Google.")
if token_response.status_code != 200:
    abort(f"Google Drive OAuth token refresh failed (HTTP {token_response.status_code}, error={oauth_error_code(token_response)}).")
token_body = checked_json(token_response, "Google Drive OAuth token refresh")
access_token = token_body.get("access_token")
if token_response.status_code != 200 or not access_token:
    abort("Google Drive OAuth token refresh did not return an access token.")
headers = {"Authorization": "Bearer " + str(access_token)}

query = (
    "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
    "and appProperties has { key='makeupart_root' and value='v1' }"
)
try:
    response = session.get(
        API + "/files",
        headers=headers,
        params={"q": query, "pageSize": 2, "fields": "files(id,mimeType)"},
        timeout=(10, 30),
    )
except requests.RequestException:
    abort("Google Drive media-root lookup could not reach Google.")
roots = checked_json(response, "Google Drive media-root lookup").get("files", [])
if response.status_code != 200 or not isinstance(roots, list) or len(roots) != 1:
    abort("Expected exactly one MakeUpArt private media folder. No backup was uploaded.")
root_id = str(roots[0].get("id", ""))
if not root_id:
    abort("Google Drive returned an invalid media-root record.")

inventory = []
page_token = None
seen_page_tokens = set()
while True:
    params = {
        "q": "'" + root_id.replace("\\", "\\\\").replace("'", "\\'") + "' in parents and trashed = false",
        "pageSize": 1000,
        "fields": "nextPageToken,files(id,mimeType,size,md5Checksum,appProperties)",
    }
    if page_token:
        if page_token in seen_page_tokens:
            abort("Google Drive repeated a pagination token; refusing an incomplete media backup.")
        seen_page_tokens.add(page_token)
        params["pageToken"] = page_token
    try:
        response = session.get(API + "/files", headers=headers, params=params, timeout=(10, 45))
    except requests.RequestException:
        abort("Google Drive media inventory could not be retrieved.")
    page = checked_json(response, "Google Drive media inventory")
    if response.status_code != 200:
        abort("Google Drive media inventory could not be retrieved.")
    batch = page.get("files", [])
    if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
        abort("Google Drive returned an invalid media inventory page.")
    inventory.extend(batch)
    if len(inventory) > 10000:
        abort("Google Drive media inventory exceeds the safe 10,000-object backup limit.")
    page_token = page.get("nextPageToken")
    if not page_token:
        break

destination_root = Path(sys.argv[1]).resolve()
manifest_path = Path(sys.argv[2])
entries = []
seen_paths = set()
total_bytes = 0

for record in inventory:
    file_id = str(record.get("id", ""))
    path_key = str((record.get("appProperties") or {}).get("makeupart_path", ""))
    relative = PurePosixPath(path_key)
    if not file_id or not path_key or relative.is_absolute() or "\\" in path_key:
        abort("A Drive media item has an invalid private path index; backup stopped.")
    if len(path_key.encode("utf-8")) > 105:
        abort("A Drive media item has an unsupported private path length; backup stopped.")
    if relative.as_posix() != path_key or any(part in ("", ".", "..") for part in relative.parts):
        abort("A Drive media item has an unsafe private path index; backup stopped.")
    if path_key in seen_paths:
        abort("Duplicate private media path indexes were found; backup stopped.")
    seen_paths.add(path_key)
    mime_type = str(record.get("mimeType") or "")
    if mime_type.startswith("application/vnd.google-apps."):
        abort("Unsupported Google Workspace item found in the media root; backup stopped safely.")
    try:
        expected_size = int(record.get("size") or 0)
    except (ValueError, TypeError):
        abort("Google Drive returned an invalid media size.")
    if expected_size > MAX_FILE_BYTES:
        abort("A media item exceeds the supported 512 MiB restore limit; no partial backup was uploaded.")
    if expected_size and total_bytes + expected_size > MAX_TOTAL_BYTES:
        abort("Media exceeds the safe 3 GiB backup limit; no partial backup was uploaded.")

    output_path = destination_root.joinpath(*relative.parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    url = API + "/files/" + quote(file_id, safe="")
    try:
        with session.get(
            url,
            headers=headers,
            params={"alt": "media"},
            stream=True,
            timeout=(10, 120),
        ) as media_response:
            if media_response.status_code != 200:
                abort(f"Private media download failed (HTTP {media_response.status_code}); media ID withheld.")
            with output_path.open("wb") as output:
                for chunk in media_response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    total_bytes += len(chunk)
                    if size > MAX_FILE_BYTES or total_bytes > MAX_TOTAL_BYTES:
                        abort("Media download exceeded the safe backup size limit; no partial backup was uploaded.")
                    digest.update(chunk)
                    md5.update(chunk)
                    output.write(chunk)
    except requests.RequestException:
        abort("A private media download failed; Google Drive identifiers and contents were withheld.")
    if size == 0:
        abort("An empty media object was found; refusing a backup that cannot be restored by the app.")
    if expected_size and size != expected_size:
        abort("Private media size verification failed; refusing to back up a truncated file.")
    expected_md5 = str(record.get("md5Checksum") or "").lower()
    if expected_md5 and md5.hexdigest().lower() != expected_md5:
        abort("Private media checksum verification failed; refusing to back up a corrupted file.")
    entries.append({
        "path": path_key,
        "size": size,
        "sha256": digest.hexdigest(),
        "md5": md5.hexdigest(),
    })

entries.sort(key=lambda item: item["path"])
manifest = {
    "format": "makeupart-google-drive-media-backup-v1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "file_count": len(entries),
    "total_bytes": total_bytes,
    "files": entries,
}
manifest_path.write_text(
    json.dumps(manifest, separators=(",", ":"), sort_keys=True),
    encoding="utf-8",
)
print(f"Private Google Drive inventory captured: files={len(entries)}, bytes={total_bytes}. File paths, IDs, tokens and image contents were not logged.")
if not entries:
    print("::warning::The MakeUpArt private media folder is empty. Backup mechanics can be verified, but recovery of customer photos/logos is not yet proven.")
