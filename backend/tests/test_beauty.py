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
from tests.utils import API, auth_headers, register, register_platform_admin


def test_makeup_style_presets_apply_face_guided_tints():
    # Synthetic 478-point mesh gives the test a bounded face oval and a lip
    # contour; this verifies the pixel operation without downloading models.
    coordinates = [(0.5, 0.5)] * 478
    coordinates[10] = (0.50, 0.12)
    coordinates[152] = (0.50, 0.90)
    coordinates[234] = (0.20, 0.50)
    coordinates[454] = (0.80, 0.50)
    coordinates[61] = (0.40, 0.62)
    coordinates[146] = (0.42, 0.60)
    coordinates[91] = (0.44, 0.59)
    coordinates[181] = (0.46, 0.585)
    coordinates[84] = (0.48, 0.60)
    coordinates[17] = (0.50, 0.605)
    coordinates[314] = (0.52, 0.60)
    coordinates[405] = (0.54, 0.585)
    coordinates[321] = (0.56, 0.59)
    coordinates[375] = (0.58, 0.60)
    coordinates[291] = (0.60, 0.62)
    coordinates[308] = (0.585, 0.625)
    coordinates[324] = (0.565, 0.635)
    coordinates[318] = (0.545, 0.642)
    coordinates[402] = (0.525, 0.647)
    coordinates[317] = (0.505, 0.65)
    coordinates[14] = (0.485, 0.65)
    coordinates[87] = (0.465, 0.645)
    coordinates[178] = (0.445, 0.638)
    coordinates[88] = (0.425, 0.63)
    coordinates[95] = (0.41, 0.625)
    coordinates[78] = (0.40, 0.62)
    # Upper eyelid contours (outer corner to inner corner) for the refined mesh.
    left_eye = {
        33: (0.34, 0.42), 246: (0.36, 0.405), 161: (0.38, 0.395),
        160: (0.40, 0.388), 159: (0.42, 0.385), 158: (0.44, 0.388),
        157: (0.46, 0.395), 173: (0.48, 0.405), 133: (0.49, 0.42),
    }
    right_eye = {
        263: (0.66, 0.42), 466: (0.64, 0.405), 388: (0.62, 0.395),
        387: (0.60, 0.388), 386: (0.58, 0.385), 385: (0.56, 0.388),
        384: (0.54, 0.395), 398: (0.52, 0.405), 362: (0.51, 0.42),
    }
    for index, point in {**left_eye, **right_eye}.items():
        coordinates[index] = point
    landmarks = SimpleNamespace(
        landmark=[SimpleNamespace(x=x, y=y) for x, y in coordinates]
    )
    source = np.full((256, 256, 3), 150, dtype=np.uint8)

    natural = BeautyProvider._apply_makeup(
        source.copy(), landmarks, "natural", 1.0
    )
    evening = BeautyProvider._apply_makeup(
        source.copy(), landmarks, "evening_glam", 1.0
    )

    assert not np.array_equal(source, natural)
    assert not np.array_equal(natural, evening)
    # The glam preset must alter the upper-eye area independently of the lips
    # and cheeks; natural mode remains deliberately subtle there.
    eye_region = np.s_[85:112, 85:125]
    assert np.mean(
        np.abs(natural[eye_region].astype(np.float32) - evening[eye_region].astype(np.float32))
    ) > 1.0
    assert np.array_equal(source, np.full((256, 256, 3), 150, dtype=np.uint8))

    # These additional presets are genuinely targeted effects, not just labels
    # that silently fall back to the natural preset.
    targeted = {}
    for style in ("smokey_eye", "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush"):
        targeted[style] = BeautyProvider._apply_makeup(
            source.copy(), landmarks, style, 1.0
        )
        assert not np.array_equal(source, targeted[style]), style

    assert not np.array_equal(
        source[eye_region], targeted["eyeshadow"][eye_region]
    )
    assert not np.array_equal(
        source[eye_region], targeted["eyeliner"][eye_region]
    )
    lip_region = np.s_[145:170, 96:160]
    assert not np.array_equal(
        source[lip_region], targeted["lipstick"][lip_region]
    )
    cheek_region = np.s_[160:190, 80:180]
    assert not np.array_equal(
        source[cheek_region], targeted["blush"][cheek_region]
    )

    # Skin-only deliberately leaves cosmetic overlay pixels unchanged; the
    # independent face-smoothing stage runs before this method.
    skin_only = BeautyProvider._apply_makeup(
        source.copy(), landmarks, "skin_only", 1.0
    )
    assert np.array_equal(source, skin_only)


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


def test_beauty_upload_rolls_back_before_commit_if_response_validation_fails(
    client, monkeypatch, tmp_path
):
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

    def invalid_response(**_kwargs):
        raise ValueError("simulated response schema validation failure")

    monkeypatch.setattr(BeautyProvider, "process", fake_process)
    monkeypatch.setattr(beauty_api, "BeautyUploadResponse", invalid_response)

    before_usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert before_usage.status_code == 200
    usage_before = before_usage.json()["used"]

    response = client.post(
        f"{API}/beauty/process-upload?intensity=0.8&consent_confirmed=true",
        headers=headers,
        files={
            "file": (
                "portrait.png",
                cv2.imencode(".png", np.full((16, 16, 3), 120, dtype=np.uint8))[1].tobytes(),
                "image/png",
            )
        },
    )

    assert response.status_code == 500
    jobs = client.get(f"{API}/beauty/jobs", headers=headers)
    assert jobs.status_code == 200
    assert jobs.json() == []

    after_usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert after_usage.status_code == 200
    assert after_usage.json()["used"] == usage_before

    salon_media = media_root / "salons" / salon_id
    remaining_media = [
        path for path in salon_media.rglob("*")
        if path.is_file() and not path.name.endswith(".rollback")
    ]
    assert remaining_media == []


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



def test_beauty_capabilities_report_provider_readiness_without_exposing_key(
    client, monkeypatch
):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    monkeypatch.setattr("app.api.v1.beauty.settings.OPENAI_API_KEY", "")
    disabled = client.get(f"{API}/beauty/capabilities", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["classic_available"] is True
    assert disabled.json()["generative_available"] is False
    assert "OPENAI_API_KEY" not in disabled.text

    monkeypatch.setattr("app.api.v1.beauty.settings.OPENAI_API_KEY", "configured-test-key")
    enabled = client.get(f"{API}/beauty/capabilities", headers=headers)
    assert enabled.status_code == 200
    assert enabled.json()["generative_available"] is True
    assert enabled.json()["generative_provider"] == "OpenAI"
    assert "configured-test-key" not in enabled.text


def test_generative_upload_requires_external_provider_consent(
    client, monkeypatch, tmp_path
):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    monkeypatch.setattr("app.api.v1.beauty.settings.OPENAI_API_KEY", "configured-test-key")
    image_bytes = cv2.imencode(
        ".png", np.full((32, 32, 3), 120, dtype=np.uint8)
    )[1].tobytes()

    response = client.post(
        f"{API}/beauty/process-upload?engine=generative&consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )
    assert response.status_code == 403
    assert "external generative AI provider" in response.json()["detail"]
    input_dir = media_root / "salons" / salon_id / "inputs"
    assert not input_dir.exists() or not list(input_dir.glob("*"))



def test_upload_fails_when_saved_salon_logo_cannot_be_restored(
    client, monkeypatch, tmp_path
):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    def fake_classic_process(self, image_path, options=None):
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / "classic-test.png"
        assert cv2.imwrite(str(output), np.full((256, 256, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_classic_process)
    monkeypatch.setattr(
        beauty_api,
        "get_or_create_watermark",
        lambda _db, _salon: SimpleNamespace(
            logo_url="/api/v1/watermarks/me/logo",
            position="bottom-right",
            size=12,
            opacity=0.5,
            phone=False,
            instagram=False,
            tiktok=False,
        ),
    )
    monkeypatch.setattr(
        beauty_api.google_drive_media, "ensure_local_file", lambda _path: False
    )

    image_bytes = cv2.imencode(
        ".png", np.full((256, 256, 3), 120, dtype=np.uint8)
    )[1].tobytes()
    response = client.post(
        f"{API}/beauty/process-upload?engine=classic&consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )

    assert response.status_code == 503
    assert "logo could not be restored" in response.json()["detail"]
    assert not list((media_root / "salons" / salon_id / "inputs").glob("*"))


def test_generative_upload_saves_watermarked_result_without_fake_identity_score(
    client, monkeypatch, tmp_path
):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]

    # Generative processing now costs the provider per image, so this integration
    # test explicitly provisions a paid plan instead of assuming free users can
    # invoke the endpoint merely because a test API key exists.
    _, admin_headers = register_platform_admin(client, monkeypatch)
    activated = client.post(
        f"{API}/admin/subscriptions/{salon_id}/activate",
        headers=admin_headers,
        json={"plan": "pro", "days": 30},
    )
    assert activated.status_code == 200, activated.text

    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))
    monkeypatch.setattr(
        "app.api.v1.beauty.settings.OPENAI_API_KEY", "configured-test-key"
    )

    calls = {"classic": 0, "generative": 0}

    def fake_classic_process(self, image_path, options=None):
        calls["classic"] += 1
        output_dir = media_root / "salons" / salon_id / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"classic-analysis-{calls['classic']}.png"
        assert cv2.imwrite(str(output), np.full((256, 256, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    def fake_generative_process(self, image_path, options=None):
        calls["generative"] += 1
        assert options["generative_look"] == "smokey_eye"
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / "generated-test.png"
        assert cv2.imwrite(str(output), np.full((256, 256, 3), 90, dtype=np.uint8))
        return {
            "processed": True,
            "engine": "generative",
            "generative_look": options["generative_look"],
            "output_path": str(output),
        }

    monkeypatch.setattr(BeautyProvider, "process", fake_classic_process)
    monkeypatch.setattr(
        beauty_api.GenerativeMakeupProvider, "process", fake_generative_process
    )
    monkeypatch.setattr(
        beauty_api.GenerativeMakeupProvider,
        "is_ready",
        classmethod(lambda cls: True),
    )

    image_bytes = cv2.imencode(
        ".png", np.full((256, 256, 3), 120, dtype=np.uint8)
    )[1].tobytes()
    response = client.post(
        f"{API}/beauty/process-upload"
        "?engine=generative&generative_look=smokey_eye"
        "&external_ai_consent=true&consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["engine"] == "generative"
    assert payload["generative_look"] == "smokey_eye"
    assert payload["identity_similarity"] is None
    assert payload["watermark_applied"] is True
    assert calls == {"classic": 1, "generative": 1}

    job_image = client.get(
        f"{API}/beauty/jobs/{payload['job_id']}/image?kind=after",
        headers=headers,
    )
    assert job_image.status_code == 200
    job_record = client.get(
        f"{API}/beauty/jobs/{payload['job_id']}", headers=headers
    )
    assert job_record.status_code == 200
    assert "External generative AI consent confirmed" in job_record.json()["notes"]
    assert "look=smokey_eye" in job_record.json()["notes"]

def test_selected_photo_finish_changes_the_persisted_upload_result(
    client, monkeypatch, tmp_path
):
    registration = register(client, email="finish-owner@salon.com")
    headers = auth_headers(client, "finish-owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    def fake_process(self, image_path, options=None):
        output = media_root / "salons" / salon_id / "outputs" / "generated.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        assert cv2.imwrite(str(output), np.full((32, 32, 3), 120, dtype=np.uint8))
        return {
            "identity_similarity": 0.99,
            "skin_tone": "medium",
            "undertone": "neutral",
            "foundation_match": "medium-neutral",
            "processed": True,
            "output_path": str(output),
        }

    # Keep this an isolated pixel-level integration test: storage and salon
    # branding should not hide a broken finish application.
    monkeypatch.setattr(BeautyProvider, "process", fake_process)
    monkeypatch.setattr(beauty_api, "apply_watermark", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        beauty_api.google_drive_media, "persist_media_file", lambda *_args, **_kwargs: False
    )

    source = np.full((32, 32, 3), 120, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", source)
    assert ok

    response = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&photo_finish=Warm%20Glow",
        headers=headers,
        files={"file": ("portrait.png", encoded.tobytes(), "image/png")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["photo_finish"] == "Warm Glow"

    before = client.get(body["before_image_url"], headers=headers)
    after = client.get(body["after_image_url"], headers=headers)
    assert before.status_code == 200
    assert after.status_code == 200

    before_pixels = cv2.imdecode(np.frombuffer(before.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    after_pixels = cv2.imdecode(np.frombuffer(after.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert before_pixels is not None
    assert after_pixels is not None
    assert before_pixels.shape == after_pixels.shape
    assert not np.array_equal(after_pixels, before_pixels), (
        "The API must return pixels that reflect the selected photo finish, not just its label."
    )

