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
    image_path = tmp_path / "portrait.png"
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


def test_beauty_process_rejects_missing_image(client, monkeypatch):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    response = client.post(
        f"{API}/beauty/process",
        headers=headers,
        json={"image_path": "/missing/portrait.png"},
    )

    assert response.status_code == 404


def test_identity_guard_does_not_invent_similarity():
    intensity, accepted = IdentityGuard().validate(0.5, 0.8)

    assert intensity == 0.8
    assert accepted is False
