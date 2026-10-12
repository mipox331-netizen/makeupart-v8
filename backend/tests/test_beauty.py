import struct
import uuid
import zlib
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi import HTTPException

from app.api.v1 import beauty as beauty_api
from app.services.beauty import BeautyProvider, IdentityGuard, SkinToneMatcher
from tests.utils import API, auth_headers, register


def test_skin_tone_detection_uses_image_pixels():
    matcher = SkinToneMatcher()
    landmarks = SimpleNamespace(
        landmark=[
            SimpleNamespace(x=0.2, y=0.2),
            SimpleNamespace(x=0.8, y=0.2),
            SimpleNamespace(x=0.8, y=0.85),
            SimpleNamespace(x=0.2, y=0.85),
        ]
    )
    light = np.full((128, 128, 3), 210, dtype=np.uint8)
    deep = np.full((128, 128, 3), 110, dtype=np.uint8)

    light_result = matcher.detect(light, landmarks)
    deep_result = matcher.detect(deep, landmarks)

    assert light_result["tone"] == "very-light"
    assert deep_result["tone"] == "deep"
    assert light_result["tone"] != deep_result["tone"]


def test_legacy_customer_flag_cannot_bypass_missing_stored_consent(monkeypatch):
    customer_id = uuid.uuid4()
    salon_id = uuid.uuid4()
    legacy_customer = SimpleNamespace(
        id=customer_id,
        salon_id=salon_id,
        consent_required=False,
    )
    db = SimpleNamespace(get=lambda model, requested_id: legacy_customer)
    user = SimpleNamespace(salon_id=salon_id)
    monkeypatch.setattr(beauty_api, "get_active_consent", lambda *_args: None)

    with pytest.raises(HTTPException) as exc:
        beauty_api._require_consent(
            db,
            user,
            customer_id=customer_id,
            consent_confirmed=True,
        )

    assert exc.value.status_code == 403
    assert "Active customer consent" in exc.value.detail


def test_oversized_image_rejected_before_opencv_decode(tmp_path, monkeypatch):
    width, height = 100_000, 100_000
    def chunk(kind, data):
        payload = kind + data
        return (
            struct.pack(">I", len(data))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">II", width, height) + bytes([8, 2, 0, 0, 0])
    # Pillow detects the declared dimensions on open; a full set of PNG
    # chunks ensures the fixture tests a huge image, not a malformed file.
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", b"")
        + chunk(b"IEND", b"")
    )
    image_path = tmp_path / "oversized.png"
    image_path.write_bytes(png)

    def no_decode(*_args, **_kwargs):
        pytest.fail("OpenCV must not decode an image whose header exceeds the pixel limit")

    monkeypatch.setattr(beauty_api.cv2, "imdecode", no_decode)
    with pytest.raises(HTTPException) as exc:
        beauty_api._validate_uploaded_image(image_path)

    assert exc.value.status_code == 413


def test_beauty_process_requires_auth(client):
    response = client.post(
        f"{API}/beauty/process",
        json={"image_path": "/tmp/face.jpg", "intensity": 0.7, "melanin_index": 2.1, "consent_confirmed": True},
    )
    assert response.status_code == 401


def test_beauty_process_satisfies_identity_threshold(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    image_path = media_root / "salons" / salon_id / "inputs" / "portrait.png"
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
    monkeypatch.setattr(BeautyProvider, "_face_mesh_available", classmethod(lambda cls: True))
    monkeypatch.setattr(BeautyProvider, "_get_face_mesh", classmethod(lambda cls: face_mesh))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(image_path), "intensity": 0.8, "melanin_index": 3.5, "consent_confirmed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed"] is True
    assert body["identity_similarity"] >= 0.85
    assert body["skin_tone"] in {"light", "medium", "olive", "deep"}
    assert body["undertone"] in {"neutral", "warm", "cool"}
    assert body["foundation_match"]


def test_beauty_process_rejects_missing_image(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={
            "image_path": str(media_root / "salons" / salon_id / "inputs" / "missing.png"),
            "consent_confirmed": True,
        },
    )

    assert response.status_code == 404


def test_beauty_process_rejects_path_outside_media_root(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(media_root / "salons" / "other" / "secret.png"), "consent_confirmed": True},
    )

    assert response.status_code == 400


def test_structure_similarity_is_one_for_identical_face_images():
    landmarks = SimpleNamespace(
        landmark=[
            SimpleNamespace(x=0.2, y=0.2),
            SimpleNamespace(x=0.8, y=0.2),
            SimpleNamespace(x=0.8, y=0.85),
            SimpleNamespace(x=0.2, y=0.85),
        ]
    )
    image = np.full((128, 128, 3), 150, dtype=np.uint8)

    similarity = IdentityGuard.measure_similarity(image, image.copy(), landmarks)

    assert similarity == pytest.approx(1.0, abs=1e-6)
    assert IdentityGuard().validate(similarity, 0.8)[1] is True


def test_structure_similarity_rejects_large_visual_changes():
    landmarks = SimpleNamespace(
        landmark=[
            SimpleNamespace(x=0.2, y=0.2),
            SimpleNamespace(x=0.8, y=0.2),
            SimpleNamespace(x=0.8, y=0.85),
            SimpleNamespace(x=0.2, y=0.85),
        ]
    )
    original = np.full((128, 128, 3), 70, dtype=np.uint8)
    changed = np.full((128, 128, 3), 235, dtype=np.uint8)

    similarity = IdentityGuard.measure_similarity(original, changed, landmarks)

    assert 0.0 <= similarity < IdentityGuard.min_similarity
    assert IdentityGuard().validate(similarity, 0.8)[1] is False


def test_identity_guard_does_not_invent_similarity():
    intensity, accepted = IdentityGuard().validate(0.5, 0.8)

    assert intensity == 0.8
    assert accepted is False


def test_beauty_upload_persists_and_secures_images(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    def fake_process(self, image_path, options=None):
        output = media_root / "salons" / salon_id / "outputs" / "generated.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(output), np.full((16, 16, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_process)

    response = client.post(
        f"{API}/beauty/process-upload?intensity=0.8&melanin_index=3.5&consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", cv2.imencode(".png", np.full((16, 16, 3), 120, dtype=np.uint8))[1].tobytes(), "image/png")},
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
    listed = client.get(f"{API}/beauty/jobs", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["job_id"]

    detail = client.get(f"{API}/beauty/jobs/{body['job_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"


def test_beauty_upload_rejects_unsupported_type(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.post(
        f"{API}/beauty/process-upload",
        headers=headers,
        files={"file": ("payload.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 415


def test_beauty_process_requires_explicit_consent(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    image_path = media_root / "salons" / salon_id / "inputs" / "portrait.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    assert cv2.imwrite(str(image_path), np.full((16, 16, 3), 120, dtype=np.uint8))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(image_path)},
    )
    assert response.status_code == 403


def test_beauty_process_cannot_cross_salon_media_roots(client, monkeypatch, tmp_path):
    registration_a = register(client, email="owner.a@salon.com", salon_name="Salon A")
    register(client, email="owner.b@salon.com", salon_name="Salon B")
    headers_a = auth_headers(client, "owner.a@salon.com")
    # Create a file in another salon's storage root.
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    foreign_path = media_root / "salons" / "foreign-salon" / "inputs" / "secret.png"
    foreign_path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(foreign_path), np.full((16, 16, 3), 120, dtype=np.uint8))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers_a,
        json={
            "image_path": str(foreign_path),
            "consent_confirmed": True,
        },
    )
    assert response.status_code == 400


def test_customer_linked_beauty_requires_stored_consent(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    customer = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Consent", "last_name": "Client", "consent_required": True},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    def fake_process(self, image_path, options=None):
        output = media_root / "salons" / salon_id / "outputs" / "generated.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(output), np.full((16, 16, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_process)
    image_bytes = cv2.imencode(
        ".png", np.full((16, 16, 3), 120, dtype=np.uint8)
    )[1].tobytes()

    blocked = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&customer_id={customer_id}",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )
    assert blocked.status_code == 403

    granted = client.post(
        f"{API}/consents",
        headers=headers,
        json={
            "customer_id": customer_id,
            "granted": True,
            "consent_text": "Client consented to AI beauty processing.",
        },
    )
    assert granted.status_code == 201

    allowed = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&customer_id={customer_id}",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )
    assert allowed.status_code == 201


def test_beauty_retries_with_lower_intensity_when_identity_guard_fails(
    client, monkeypatch, tmp_path
):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    calls = []

    def fake_process(self, image_path, options=None):
        intensity = float((options or {}).get("intensity", 0.7))
        calls.append(intensity)
        output = media_root / "salons" / salon_id / "outputs" / f"attempt-{len(calls)}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(output), np.full((16, 16, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.80 if len(calls) == 1 else 0.90,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_process)
    image_path = media_root / "salons" / salon_id / "inputs" / "portrait.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(image_path), np.full((16, 16, 3), 120, dtype=np.uint8))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={
            "image_path": str(image_path),
            "intensity": 0.9,
            "consent_confirmed": True,
        },
    )
    assert response.status_code == 200
    assert len(calls) == 2
    assert calls[1] < calls[0]
    assert response.json()["identity_similarity"] == 0.9


def test_beauty_process_rejects_multiple_faces(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    image_path = media_root / "salons" / salon_id / "inputs" / "group.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    assert cv2.imwrite(str(image_path), np.full((64, 64, 3), 180, dtype=np.uint8))

    landmarks_a = SimpleNamespace(landmark=[SimpleNamespace(x=0.2, y=0.2)])
    landmarks_b = SimpleNamespace(landmark=[SimpleNamespace(x=0.8, y=0.2)])
    face_mesh = SimpleNamespace(
        process=lambda image: SimpleNamespace(
            multi_face_landmarks=[landmarks_a, landmarks_b]
        )
    )
    monkeypatch.setattr(BeautyProvider, "_face_mesh_available", classmethod(lambda cls: True))
    monkeypatch.setattr(BeautyProvider, "_get_face_mesh", classmethod(lambda cls: face_mesh))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={
            "image_path": str(image_path),
            "intensity": 0.7,
            "melanin_index": 2.0,
            "consent_confirmed": True,
        },
    )

    assert response.status_code == 422
    assert "exactly one face" in response.json()["detail"]
