import io
import uuid

import cv2
import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.models.salon import Salon
from app.models.watermark import Watermark
from app.schemas.watermark import WatermarkUpdate
from app.services.google_drive_media import GoogleDriveMediaError
from app.services.watermark import apply_watermark
from tests.utils import API, auth_headers, register


def test_apply_watermark_changes_image(tmp_path):
    path = tmp_path / "output.png"
    source = np.full((480, 640, 3), 240, dtype=np.uint8)
    assert cv2.imwrite(str(path), source)

    salon = Salon(name="Tony Beauty Studio")
    watermark = Watermark(
        salon_name=False,
        phone=False,
        instagram=False,
        tiktok=False,
        position="bottom-right",
        opacity=0.5,
        size=12,
    )

    applied = apply_watermark(path, salon, watermark)

    result = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert applied is True
    assert result is not None
    assert not np.array_equal(source, result)


def test_uploaded_transparent_logo_is_composited_onto_result(tmp_path, monkeypatch):
    salon_id = uuid.uuid4()
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.services.watermark.settings.MEDIA_ROOT", str(media_root))

    logo_directory = media_root / "salons" / str(salon_id) / "branding"
    logo_directory.mkdir(parents=True)
    logo_path = logo_directory / "logo.png"
    logo = Image.new("RGBA", (100, 50), (240, 30, 80, 255))
    logo.save(logo_path)

    path = tmp_path / "output.png"
    source = np.full((480, 640, 3), 240, dtype=np.uint8)
    assert cv2.imwrite(str(path), source)
    salon = Salon(id=salon_id, name="Tony Beauty Studio")
    watermark = Watermark(
        logo_url="/api/v1/watermarks/me/logo",
        salon_name=True,
        position="bottom-left",
        opacity=1.0,
        size=12,
    )

    apply_watermark(path, salon, watermark)
    result = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert result is not None
    assert not np.array_equal(source, result)
    # Opaque red pixels from the logo must survive the RGBA-to-BGR overlay.
    assert np.any((result[:, :, 2] > 180) & (result[:, :, 0] < 100))


def test_clients_cannot_disable_required_salon_name():
    with pytest.raises(ValidationError):
        WatermarkUpdate(salon_name=False)


def test_owner_can_upload_and_retrieve_salon_logo(client, tmp_path, monkeypatch):
    registration = register(client)
    assert registration.status_code == 201
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.watermarks.settings.MEDIA_ROOT", str(media_root))

    buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (60, 30, 180, 150)).save(buffer, format="PNG")
    payload = buffer.getvalue()

    uploaded = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("salon-logo.png", payload, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["logo_url"] == "/api/v1/watermarks/me/logo"

    retrieved = client.get(f"{API}/watermarks/me/logo", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.headers["content-type"].startswith("image/png")
    with Image.open(io.BytesIO(retrieved.content)) as image:
        assert image.mode == "RGBA"
        assert image.size == (64, 32)

    settings_response = client.patch(
        f"{API}/watermarks/me",
        headers=headers,
        json={
            "salon_name": True,
            "position": "top-left",
            "opacity": 0.8,
            "size": 24,
            "phone": True,
            "instagram": False,
            "tiktok": True,
        },
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["position"] == "top-left"
    assert settings_response.json()["opacity"] == pytest.approx(0.8)
    assert settings_response.json()["size"] == 24
    assert settings_response.json()["phone"] is True


def test_failed_logo_replacement_restores_previous_local_logo(client, tmp_path, monkeypatch):
    registration = register(client)
    assert registration.status_code == 201
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.watermarks.settings.MEDIA_ROOT", str(media_root))

    first_buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (220, 30, 60, 255)).save(first_buffer, format="PNG")
    first_payload = first_buffer.getvalue()
    first = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("old-logo.png", first_payload, "image/png")},
    )
    assert first.status_code == 200, first.text

    salon_id = registration.json()["salon"]["id"]
    target = media_root / "salons" / salon_id / "branding" / "logo.png"
    old_bytes = target.read_bytes()

    second_buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (20, 100, 220, 255)).save(second_buffer, format="PNG")
    calls = 0

    def fail_replacement_once(_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise GoogleDriveMediaError("simulated Drive write failure")
        # Development mode does not require durable Drive storage.
        return False

    monkeypatch.setattr(
        "app.api.v1.watermarks.google_drive_media.persist_media_file",
        fail_replacement_once,
    )
    failed = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("new-logo.png", second_buffer.getvalue(), "image/png")},
    )

    assert failed.status_code == 503
    assert target.read_bytes() == old_bytes
    retrieved = client.get(f"{API}/watermarks/me/logo", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.content == old_bytes
    assert list(target.parent.glob("*.rollback")) == []


def test_failed_first_logo_upload_removes_unreferenced_local_logo(client, tmp_path, monkeypatch):
    registration = register(client)
    assert registration.status_code == 201
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.watermarks.settings.MEDIA_ROOT", str(media_root))

    buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (40, 180, 90, 255)).save(buffer, format="PNG")

    monkeypatch.setattr(
        "app.api.v1.watermarks.google_drive_media.persist_media_file",
        lambda _path: (_ for _ in ()).throw(
            GoogleDriveMediaError("simulated Drive write failure")
        ),
    )
    failed = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("first-logo.png", buffer.getvalue(), "image/png")},
    )

    assert failed.status_code == 503
    salon_id = registration.json()["salon"]["id"]
    target = media_root / "salons" / salon_id / "branding" / "logo.png"
    assert not target.exists()
    assert not list(target.parent.glob("*.rollback")) if target.parent.exists() else True
    retrieved = client.get(f"{API}/watermarks/me/logo", headers=headers)
    assert retrieved.status_code == 404


def test_apply_watermark_rejects_logo_symlink_escape(tmp_path, monkeypatch):
    salon_id = uuid.uuid4()
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.services.watermark.settings.MEDIA_ROOT", str(media_root))

    salons_dir = media_root / "salons"
    salons_dir.mkdir(parents=True)
    outside_dir = media_root / "outside-salon"
    outside_dir.mkdir()
    (salons_dir / str(salon_id)).symlink_to(outside_dir, target_is_directory=True)

    image_path = tmp_path / "output.png"
    assert cv2.imwrite(str(image_path), np.full((120, 160, 3), 240, dtype=np.uint8))
    salon = Salon(id=salon_id, name="Tony Beauty Studio")
    watermark = Watermark(
        logo_url="/api/v1/watermarks/me/logo",
        salon_name=True,
        position="bottom-right",
        opacity=0.5,
        size=12,
    )

    with pytest.raises(ValueError, match="tenant-isolation"):
        apply_watermark(image_path, salon, watermark)


def test_logo_upload_rejects_salon_directory_symlink(client, tmp_path, monkeypatch):
    registration = register(client)
    assert registration.status_code == 201
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.watermarks.settings.MEDIA_ROOT", str(media_root))

    salon_id = registration.json()["salon"]["id"]
    salons_dir = media_root / "salons"
    salons_dir.mkdir(parents=True)
    outside_dir = media_root / "other-salon"
    outside_dir.mkdir()
    (salons_dir / salon_id).symlink_to(outside_dir, target_is_directory=True)

    buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (200, 30, 40, 255)).save(buffer, format="PNG")
    response = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("logo.png", buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 500
    assert not (outside_dir / "branding" / "logo.png").exists()


def test_logo_upload_rejects_non_images(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("fake.png", b"not an image", "image/png")},
    )
    assert response.status_code == 422


def test_logo_upload_rejects_unsupported_media_type(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.post(
        f"{API}/watermarks/me/logo",
        headers=headers,
        files={"file": ("logo.svg", b"<svg/>", "image/svg+xml")},
    )
    assert response.status_code == 415
