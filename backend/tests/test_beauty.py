from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.services.beauty import BeautyProvider, IdentityGuard, SkinToneMatcher
from tests.utils import API, auth_headers, register


def test_fitzpatrick_detection_ranges_cover_all_types():
    matcher = SkinToneMatcher()
    assert matcher.detect(0.4)["tone"] == "very-light"
    assert matcher.detect(0.9)["tone"] == "light"
    assert matcher.detect(1.8)["tone"] == "medium"
    assert matcher.detect(2.5)["tone"] == "olive"
    assert matcher.detect(3.6)["tone"] == "deep"
    assert matcher.detect(5.0)["tone"] == "very-deep"


def test_beauty_process_requires_auth(client):
    response = client.post(
        f"{API}/beauty/process",
        json={"image_path": "/tmp/face.jpg", "intensity": 0.7, "melanin_index": 2.1},
    )
    assert response.status_code == 401


def test_beauty_process_satisfies_identity_threshold(client, monkeypatch, tmp_path):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    image_path = media_root / "inputs" / "portrait.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    assert cv2.imwrite(str(image_path), np.full((128, 128, 3), 180, dtype=np.uint8))

    landmarks = SimpleNamespace(
        landmark=[
            SimpleNamespace(x=0.25, y=0.2),
            SimpleNamespace(x=0.75, y=0.2),
            SimpleNamespace(x=0.75, y=0.8),
            SimpleNamespace(x=0.25, y=0.8),
        ]
    )
    face_mesh = SimpleNamespace(
        process=lambda image: SimpleNamespace(multi_face_landmarks=[landmarks])
    )
    face_app = SimpleNamespace(
        get=lambda image: [SimpleNamespace(embedding=np.array([1.0, 0.0]))]
    )
    monkeypatch.setattr(BeautyProvider, "_face_mesh_available", classmethod(lambda cls: True))
    monkeypatch.setattr(BeautyProvider, "_get_face_mesh", classmethod(lambda cls: face_mesh))
    monkeypatch.setattr(BeautyProvider, "_get_face_app", classmethod(lambda cls: face_app))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(image_path), "intensity": 0.8, "melanin_index": 3.5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed"] is True
    assert body["identity_similarity"] >= 0.85
    assert body["skin_tone"] in {"medium", "olive", "deep"}
    assert body["undertone"] in {"neutral", "warm", "cool"}
    assert body["foundation_match"]


def test_beauty_process_rejects_missing_image(client, monkeypatch, tmp_path):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(media_root / "inputs" / "missing.png")},
    )

    assert response.status_code == 404


def test_beauty_process_rejects_path_outside_media_root(client, monkeypatch, tmp_path):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(tmp_path / "media"))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(tmp_path / "secret.png")},
    )

    assert response.status_code == 400


def test_identity_guard_does_not_invent_similarity():
    intensity, accepted = IdentityGuard().validate(0.5, 0.8)

    assert intensity == 0.8
    assert accepted is False


def test_beauty_upload_persists_and_secures_images(client, monkeypatch, tmp_path):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(tmp_path / "media"))

    def fake_process(self, image_path, options=None):
        output = tmp_path / "media" / "generated.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(output), np.full((16, 16, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "processed": True,
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_process)

    response = client.post(
        f"{API}/beauty/process-upload?intensity=0.8&melanin_index=3.5",
        headers=headers,
        files={"file": ("portrait.png", b"fake-image-bytes", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processed"] is True
    assert body["identity_similarity"] == 0.99
    assert body["job_id"]
    assert body["before_image_url"].startswith("/api/v1/beauty/jobs/")
    assert body["after_image_url"].startswith("/api/v1/beauty/jobs/")

    before = client.get(body["before_image_url"], headers=headers)
    after = client.get(body["after_image_url"], headers=headers)
    assert before.status_code == 200
    assert after.status_code == 200
    assert before.headers["content-type"].startswith("image/")
    assert after.headers["content-type"].startswith("image/")


def test_beauty_upload_rejects_unsupported_type(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.post(
        f"{API}/beauty/process-upload",
        headers=headers,
        files={"file": ("payload.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 415
