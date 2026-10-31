from pathlib import Path

import httpx
import pytest

from app.core.config import settings
from app.services import google_drive_media as media


@pytest.fixture
def supabase_media(monkeypatch, tmp_path):
    root = tmp_path / "private-media"
    root.mkdir()
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(root))
    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "supabase_storage")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setattr(settings, "SUPABASE_MEDIA_BUCKET", "makeupart-media")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    return root


def response(method, url, status=200, *, json_body=None, content=b""):
    kwargs = {"json": json_body} if json_body is not None else {"content": content}
    return httpx.Response(status, request=httpx.Request(method, url), **kwargs)


def test_private_bucket_is_created_when_missing_and_never_public(supabase_media, monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        assert kwargs["headers"]["apikey"] == "test-service-role-key"
        assert kwargs["headers"]["Authorization"] == "Bearer test-service-role-key"
        if method == "GET":
            return response(method, url, 400, json_body={"code": "NoSuchBucket", "message": "Bucket not found"})
        if method == "POST":
            assert url.endswith("/storage/v1/bucket")
            assert kwargs["json"]["public"] is False
            return response(method, url, 200, json_body={"id": "makeupart-media", "public": False})
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(media.httpx, "request", fake_request)

    media.verify_connection()

    assert [item[0] for item in calls] == ["GET", "POST"]


def test_supabase_upload_verifies_stored_bytes_and_keeps_private_object_key(
    supabase_media, monkeypatch
):
    photo = supabase_media / "salons" / "salon-a" / "outputs" / "after.png"
    photo.parent.mkdir(parents=True)
    payload = b"private processed image"
    photo.write_bytes(payload)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "POST":
            assert url.endswith("/storage/v1/object/makeupart-media/salons/salon-a/outputs/after.png")
            assert kwargs["headers"]["x-upsert"] == "true"
            assert kwargs["headers"]["Content-Type"] == "image/png"
            assert kwargs["content"] == payload
            return response(method, url, 200, json_body={"Key": "makeupart-media/salons/salon-a/outputs/after.png"})
        if method == "GET":
            return response(method, url, 200, content=payload)
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(media.httpx, "request", fake_request)

    assert media.persist_media_file(photo) is True
    assert [call[0] for call in calls] == ["POST", "GET"]


def test_supabase_restore_writes_private_media_atomically(supabase_media, monkeypatch):
    photo = supabase_media / "salons" / "salon-a" / "inputs" / "before.jpg"
    payload = b"private customer portrait"

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/storage/v1/object/makeupart-media/salons/salon-a/inputs/before.jpg")
        return response(method, url, 200, content=payload)

    monkeypatch.setattr(media.httpx, "request", fake_request)

    assert media.ensure_local_file(photo) is True
    assert photo.read_bytes() == payload
    assert list(photo.parent.glob("*.tmp")) == []


def test_supabase_delete_targets_only_the_tenant_scoped_object(supabase_media, monkeypatch):
    photo = supabase_media / "salons" / "salon-a" / "inputs" / "before.jpg"
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return response(method, url, 200, json_body={"message": "deleted"})

    monkeypatch.setattr(media.httpx, "request", fake_request)

    assert media.delete_media_file(photo) is True
    assert captured["method"] == "DELETE"
    assert captured["url"].endswith("/storage/v1/object/makeupart-media")
    assert captured["kwargs"]["json"] == {
        "prefixes": ["salons/salon-a/inputs/before.jpg"]
    }


def test_supabase_rejects_public_bucket(supabase_media, monkeypatch):
    def fake_request(method, url, **kwargs):
        return response(method, url, 200, json_body={"id": "makeupart-media", "public": True})

    monkeypatch.setattr(media.httpx, "request", fake_request)

    with pytest.raises(media.GoogleDriveMediaError, match="must be private"):
        media.verify_connection()


def test_supabase_provider_fails_closed_without_server_secret(monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "supabase_storage")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setattr(settings, "SUPABASE_MEDIA_BUCKET", "makeupart-media")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)

    with pytest.raises(media.GoogleDriveMediaError, match="configuration is incomplete"):
        media.verify_connection()
