import hashlib
import json
from pathlib import Path

import pytest
import httpx

from scripts import supabase_media_backup as backup


def make_response(status, *, payload=None, content=b""):
    return httpx.Response(
        status_code=status,
        request=httpx.Request("GET", "https://project.supabase.co/storage/v1/test"),
        json=payload if payload is not None else None,
        content=content if payload is None else None,
    )


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "server-only-test-key")
    monkeypatch.setenv("SUPABASE_MEDIA_BUCKET", "makeupart-media")
    destination = tmp_path / "stage" / "media"
    manifest = tmp_path / "stage" / "manifest.json"
    return destination, manifest


def test_private_supabase_media_backup_walks_tenant_paths_and_verifies_checksums(
    monkeypatch, tmp_path
):
    destination, manifest_path = configure(monkeypatch, tmp_path)
    photo = b"private salon test image"

    def fake_request(self, method, url, headers=None, **kwargs):
        assert headers["apikey"] == "server-only-test-key"
        assert headers["Authorization"] == "Bearer server-only-test-key"
        if method == "GET" and url.endswith("/bucket/makeupart-media"):
            return make_response(200, payload={"id": "makeupart-media", "public": False})
        if method == "POST" and "/object/list/" in url:
            prefix = kwargs["json"]["prefix"]
            if prefix == "":
                rows = [{"name": "salons", "id": None, "metadata": None}]
            elif prefix == "salons":
                rows = [{"name": "salon-a", "id": None, "metadata": None}]
            elif prefix == "salons/salon-a":
                rows = [{"name": "outputs", "id": None, "metadata": None}]
            elif prefix == "salons/salon-a/outputs":
                rows = [{
                    "name": "after.png",
                    "id": "file-1",
                    "metadata": {"size": len(photo), "mimetype": "image/png"},
                }]
            else:
                rows = []
            return make_response(200, payload=rows)
        if method == "GET" and url.endswith(
            "/object/makeupart-media/salons/salon-a/outputs/after.png"
        ):
            return make_response(200, content=photo)
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    count, total = backup.backup_media(destination, manifest_path)

    assert count == 1
    assert total == len(photo)
    saved = destination / "salons" / "salon-a" / "outputs" / "after.png"
    assert saved.read_bytes() == photo
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["format"] == "makeupart-supabase-storage-media-backup-v1"
    assert manifest["files"] == [{
        "path": "salons/salon-a/outputs/after.png",
        "size": len(photo),
        "sha256": hashlib.sha256(photo).hexdigest(),
    }]


def test_backup_rejects_public_bucket(monkeypatch, tmp_path):
    destination, manifest_path = configure(monkeypatch, tmp_path)

    def fake_request(self, method, url, headers=None, **kwargs):
        return make_response(200, payload={"id": "makeupart-media", "public": True})

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with pytest.raises(backup.BackupError, match="must be private"):
        backup.backup_media(destination, manifest_path)


def test_backup_refuses_empty_media_bucket(monkeypatch, tmp_path):
    destination, manifest_path = configure(monkeypatch, tmp_path)

    def fake_request(self, method, url, headers=None, **kwargs):
        if method == "GET" and url.endswith("/bucket/makeupart-media"):
            return make_response(200, payload={"id": "makeupart-media", "public": False})
        if method == "POST":
            return make_response(200, payload=[])
        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    with pytest.raises(backup.BackupError, match="bucket is empty"):
        backup.backup_media(destination, manifest_path)
