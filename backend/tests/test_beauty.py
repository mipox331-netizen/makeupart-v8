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
    face_app = SimpleNamespace(
        get=lambda image: [SimpleNamespace(embedding=np.array([1.0, 0.0]))]
    )
    monkeypatch.setattr(BeautyProvider, "_face_mesh_available", classmethod(lambda cls: True))
    monkeypatch.setattr(BeautyProvider, "_get_face_mesh", classmethod(lambda cls: face_mesh))
    monkeypatch.setattr(BeautyProvider, "_get_face_app", classmethod(lambda cls: face_app))

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": str(image_path), "intensity": 0.8, "melanin_index": 3.5, "consent_confirmed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processed"] is True
    assert body["identity_similarity"] >= 0.85
    assert body["skin_tone"] in {"medium", "olive", "deep"}
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
    assert detail.json()["status"] == "COMPLETED"


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
