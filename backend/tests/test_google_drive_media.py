from pathlib import Path

import httpx
import pytest

from app.core.config import settings
from app.services import google_drive_media as drive


@pytest.fixture(autouse=True)
def reset_drive_caches():
    drive._TOKEN_CACHE.clear()
    drive._ROOT_CACHE.clear()
    yield
    drive._TOKEN_CACHE.clear()
    drive._ROOT_CACHE.clear()


def configure_drive(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    settings.media_root_path.mkdir(parents=True, exist_ok=True)


def make_response(url: str, status: int = 200, *, body=None, headers=None, content=b""):
    response_payload = {"json": body} if body is not None else {"content": content}
    return httpx.Response(
        status,
        headers=headers,
        request=httpx.Request("GET", url),
        **response_payload,
    )


def test_local_only_mode_is_explicit_when_drive_is_not_required(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    path = settings.media_root_path / "salons" / "test" / "input.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"image")

    assert drive.persist_media_file(path) is False
    assert drive.ensure_local_file(path.parent / "missing.png") is False
    assert drive.delete_media_file(path) is False


def test_required_mode_fails_closed_without_oauth_credentials(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)

    with pytest.raises(drive.GoogleDriveMediaError, match="not configured"):
        drive._credentials()


def test_media_key_rejects_paths_outside_media_root(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not managed media")

    with pytest.raises(drive.GoogleDriveMediaError, match="outside"):
        drive._relative_key(outside)


def test_upload_uses_private_app_folder_and_resumable_drive_upload(monkeypatch, tmp_path):
    configure_drive(monkeypatch, tmp_path)
    media_path = settings.media_root_path / "salons" / "salon-123" / "outputs" / "after.png"
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"private-makeup-image")
    api_calls = []
    uploaded_chunks = []

    def fake_token_post(url, **kwargs):
        assert url == drive._TOKEN_URL
        assert kwargs["data"]["grant_type"] == "refresh_token"
        return make_response(url, body={"access_token": "test-access-token", "expires_in": 3600})

    def fake_api_request(method, url, **kwargs):
        api_calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/files"):
            query = kwargs["params"]["q"]
            if "makeupart_root" in query:
                return make_response(url, body={"files": [{"id": "private-root"}]})
            assert "makeupart_path" in query
            return make_response(url, body={"files": []})
        if method == "POST" and url == f"{drive._UPLOAD_API}/files":
            metadata = kwargs["json"]
            assert metadata["parents"] == ["private-root"]
            assert kwargs["params"]["ignoreDefaultVisibility"] == "true"
            assert metadata["appProperties"]["makeupart_path"] == "salons/salon-123/outputs/after.png"
            assert metadata["name"].endswith("-after.png")
            return make_response(url, headers={"Location": "https://upload.test/session"})
        if method == "PUT" and url == "https://upload.test/session":
            uploaded_chunks.extend(list(kwargs["content"]))
            return make_response(url, body={"id": "saved-file", "name": "after.png"})
        raise AssertionError(f"Unexpected Google Drive API request: {method} {url}")

    monkeypatch.setattr(drive.httpx, "post", fake_token_post)
    monkeypatch.setattr(drive.httpx, "request", fake_api_request)

    assert drive.persist_media_file(media_path) is True
    assert b"".join(uploaded_chunks) == b"private-makeup-image"
    assert any(method == "PUT" for method, _, _ in api_calls)
    # No public permission or share-link operation is ever requested.
    assert all("/permissions" not in url for _, url, _ in api_calls)


def test_restore_recovers_a_missing_media_file_atomically(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "restore-client")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "restore-secret")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "restore-refresh")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    media_path = settings.media_root_path / "salons" / "salon-123" / "outputs" / "after.png"
    monkeypatch.setattr(drive, "_access_token", lambda: "test-token")
    monkeypatch.setattr(drive, "_root_folder_id", lambda _token: "private-root")
    monkeypatch.setattr(
        drive,
        "_find_media_object",
        lambda key, _token, _folder: (
            {"id": "stored-file"} if key == "salons/salon-123/outputs/after.png" else None
        ),
    )

    class FakeStream:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_bytes(self, chunk_size=1024 * 1024):
            assert chunk_size > 0
            yield b"restored-private-image"

    monkeypatch.setattr(drive.httpx, "stream", lambda *args, **kwargs: FakeStream())

    assert drive.ensure_local_file(media_path) is True
    assert media_path.read_bytes() == b"restored-private-image"
    assert list(media_path.parent.glob("*.tmp")) == []


def test_delete_trashes_only_the_matched_private_drive_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "delete-client")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "delete-secret")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "delete-refresh")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    media_path = settings.media_root_path / "salons" / "salon-123" / "inputs" / "before.jpg"
    monkeypatch.setattr(drive, "_access_token", lambda: "test-token")
    monkeypatch.setattr(drive, "_root_folder_id", lambda _token: "private-root")
    monkeypatch.setattr(
        drive,
        "_find_media_object",
        lambda *_args: {"id": "matched-file"},
    )
    recorded = {}

    def fake_request(method, url, **kwargs):
        recorded.update(method=method, url=url, **kwargs)
        return make_response(url, body={"id": "matched-file", "trashed": True})

    monkeypatch.setattr(drive, "_request", fake_request)

    assert drive.delete_media_file(media_path) is True
    assert recorded["method"] == "PATCH"
    assert recorded["url"].endswith("/files/matched-file")
    assert recorded["json"] == {"trashed": True}
