import hashlib
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


def test_production_mode_fails_closed_without_oauth_even_if_flag_is_false(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)

    with pytest.raises(drive.GoogleDriveMediaError, match="Durable media storage is required"):
        drive._credentials()


def test_partial_oauth_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "configured-client")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)

    with pytest.raises(drive.GoogleDriveMediaError, match="configuration is incomplete"):
        drive._credentials()


def test_media_key_rejects_paths_outside_media_root(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not managed media")

    with pytest.raises(drive.GoogleDriveMediaError, match="outside"):
        drive._relative_key(outside)


def test_root_folder_refuses_duplicate_private_media_roots(monkeypatch, tmp_path):
    configure_drive(monkeypatch, tmp_path)

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/files")
        assert kwargs["params"]["pageSize"] == 2
        return make_response(
            url,
            body={"files": [{"id": "private-root-a"}, {"id": "private-root-b"}]},
        )

    monkeypatch.setattr(drive, "_request", fake_request)

    with pytest.raises(drive.GoogleDriveMediaError, match="Multiple private media root folders"):
        drive._root_folder_id("test-token")


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
            return make_response(url, headers={"Location": "https://www.googleapis.com/upload/session"})
        if method == "PUT" and url == "https://www.googleapis.com/upload/session":
            uploaded_chunks.extend(list(kwargs["content"]))
            return make_response(
                url,
                body={
                    "id": "saved-file",
                    "name": "after.png",
                    "size": str(len(b"private-makeup-image")),
                    "md5Checksum": hashlib.md5(
                        b"private-makeup-image", usedforsecurity=False
                    ).hexdigest(),
                },
            )
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
            {
                "id": "stored-file",
                "md5Checksum": "89c0afcc7a35f2000404f5512f312569",
            }
            if key == "salons/salon-123/outputs/after.png"
            else None
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


def test_restore_rejects_corrupt_content_without_publishing_partial_file(monkeypatch, tmp_path):
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
        lambda *_args: {
            "id": "stored-file",
            # Expected checksum is for the original payload, not the response below.
            "md5Checksum": hashlib.md5(b"original-private-image", usedforsecurity=False).hexdigest(),
        },
    )

    class FakeStream:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_bytes(self, chunk_size=1024 * 1024):
            assert chunk_size > 0
            yield b"corrupted-private-image"

    monkeypatch.setattr(drive.httpx, "stream", lambda *args, **kwargs: FakeStream())

    with pytest.raises(drive.GoogleDriveMediaError, match="checksum mismatch"):
        drive.ensure_local_file(media_path)

    assert not media_path.exists()
    assert list(media_path.parent.glob(".after.png.*.tmp")) == []


def test_delete_permanently_removes_active_and_legacy_trashed_drive_files(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "delete-client")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "delete-secret")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "delete-refresh")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    media_path = settings.media_root_path / "salons" / "salon-123" / "inputs" / "before.jpg"
    monkeypatch.setattr(drive, "_access_token", lambda: "test-token")
    monkeypatch.setattr(drive, "_root_folder_id", lambda _token: "private-root")
    recorded_deletes = []
    recorded_queries = []

    def fake_request(method, url, **kwargs):
        if method == "GET" and url.endswith("/files"):
            query = kwargs["params"]["q"]
            recorded_queries.append(query)
            if "trashed = true" in query:
                return make_response(
                    url,
                    body={"files": [{"id": "legacy-trashed-file", "trashed": True}]},
                )
            return make_response(
                url,
                body={"files": [{"id": "current-file", "trashed": False}]},
            )
        if method == "DELETE":
            recorded_deletes.append(url)
            return make_response(url, status=204)
        raise AssertionError(f"Unexpected Google Drive request: {method} {url}")

    monkeypatch.setattr(drive, "_request", fake_request)

    assert drive.delete_media_file(media_path) is True
    assert len(recorded_queries) == 2
    assert any("trashed = false" in query for query in recorded_queries)
    assert any("trashed = true" in query for query in recorded_queries)
    assert recorded_deletes == [
        f"{drive._API}/files/current-file",
        f"{drive._API}/files/legacy-trashed-file",
    ] or set(recorded_deletes) == {
        f"{drive._API}/files/current-file",
        f"{drive._API}/files/legacy-trashed-file",
    }


def test_upload_rejects_media_when_drive_checksum_does_not_match(monkeypatch, tmp_path):
    configure_drive(monkeypatch, tmp_path)
    media_path = settings.media_root_path / "salons" / "salon-123" / "outputs" / "after.png"
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"private-makeup-image")
    monkeypatch.setattr(
        drive,
        "_access_token",
        lambda: "test-token",
    )
    monkeypatch.setattr(drive, "_root_folder_id", lambda _token: "private-root")
    monkeypatch.setattr(drive, "_find_media_object", lambda *_args: None)

    def fake_request(method, url, **kwargs):
        if method == "GET" and url.endswith("/files"):
            if "makeupart_root" in kwargs["params"]["q"]:
                return make_response(url, body={"files": [{"id": "private-root"}]})
            return make_response(url, body={"files": []})
        if method == "POST" and url == f"{drive._UPLOAD_API}/files":
            return make_response(url, headers={"Location": "https://www.googleapis.com/upload/session"})
        if method == "PUT" and url == "https://www.googleapis.com/upload/session":
            return make_response(
                url,
                body={
                    "id": "saved-file",
                    "name": "after.png",
                    "size": str(len(b"private-makeup-image")),
                    "md5Checksum": hashlib.md5(
                        b"different-image", usedforsecurity=False
                    ).hexdigest(),
                },
            )
        raise AssertionError(f"Unexpected Google Drive API request: {method} {url}")

    monkeypatch.setattr(drive, "_request", fake_request)

    with pytest.raises(drive.GoogleDriveMediaError, match="checksum verification failed"):
        drive.persist_media_file(media_path)


def test_rejects_upload_session_url_outside_google_hosts(monkeypatch, tmp_path):
    configure_drive(monkeypatch, tmp_path)
    media_path = (
        settings.media_root_path / "salons" / "salon-123" / "outputs" / "after.png"
    )
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"private-makeup-image")
    monkeypatch.setattr(drive, "_access_token", lambda: "test-token")
    monkeypatch.setattr(drive, "_root_folder_id", lambda _token: "private-root")
    monkeypatch.setattr(drive, "_find_media_object", lambda *_args: None)

    def fake_request(method, url, **kwargs):
        if method == "GET":
            return make_response(url, body={"files": []})
        return make_response(url, headers={"Location": "https://attacker.example/upload"})

    monkeypatch.setattr(drive, "_request", fake_request)
    with pytest.raises(drive.GoogleDriveMediaError, match="unsafe resumable upload URL"):
        drive.persist_media_file(media_path)
