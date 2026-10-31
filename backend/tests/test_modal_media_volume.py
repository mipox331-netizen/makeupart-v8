from pathlib import Path

import pytest

from app.core.config import settings
from app.services import google_drive_media
from app.services.google_drive_media import GoogleDriveMediaError
from app.services.media_volume import is_media_volume_configured
from app.api.v1.beauty import _persist_private_media_file


def test_modal_volume_is_used_without_google_oauth(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "modal_volume")
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr("app.services.media_volume._commit_callback", lambda: None)

    media_file = tmp_path / "salons" / "salon-a" / "photo.png"
    media_file.parent.mkdir(parents=True)
    media_file.write_bytes(b"private photo fixture")

    assert is_media_volume_configured() is True
    assert google_drive_media.uses_modal_volume() is True
    google_drive_media.verify_connection()
    assert google_drive_media.persist_media_file(media_file) is False
    assert google_drive_media.ensure_local_file(media_file) is True
    assert google_drive_media.delete_media_file(media_file) is False


def test_modal_volume_must_be_injected_before_media_readiness(monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "modal_volume")
    monkeypatch.setattr("app.services.media_volume._commit_callback", None)

    with pytest.raises(GoogleDriveMediaError, match="Modal media Volume is not mounted"):
        google_drive_media.verify_connection()


def test_production_photo_persistence_accepts_mounted_modal_volume(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MEDIA_STORAGE_BACKEND", "modal_volume")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))
    monkeypatch.setattr("app.services.media_volume._commit_callback", lambda: None)

    photo = tmp_path / "salons" / "salon-a" / "processed.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"processed photo")

    # Modal Volume durability is committed by commit_media_volume after the
    # photo and its database rows are ready; Drive persistence correctly no-ops.
    _persist_private_media_file(photo)
    assert photo.is_file()
