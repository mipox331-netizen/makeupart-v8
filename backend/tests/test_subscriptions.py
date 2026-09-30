from app.models.salon import SubscriptionPlan
from app.models.subscription import Subscription
from app.services import subscription as subscription_service
from tests.utils import API, auth_headers, register


def test_subscription_usage_defaults_to_free_plan(client):
    register(client)
    response = client.get(f"{API}/subscriptions/me", headers=auth_headers(client, "owner@salon.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["status"] == "active"
    assert body["monthly_limit"] == 25
    assert body["used"] == 0
    assert body["remaining"] == 25


def test_beauty_quota_blocks_processing_after_limit(client, monkeypatch, tmp_path):
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]
    monkeypatch.setitem(subscription_service.PLAN_LIMITS, SubscriptionPlan.FREE, 1)

    media_root = tmp_path / "media"
    monkeypatch.setattr("app.api.v1.beauty.settings.MEDIA_ROOT", str(media_root))

    import cv2
    import numpy as np
    from app.services.beauty import BeautyProvider

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
    image_bytes = cv2.imencode(".png", np.full((16, 16, 3), 120, dtype=np.uint8))[1].tobytes()

    first = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )
    assert first.status_code == 201

    second = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true",
        headers=headers,
        files={"file": ("portrait.png", image_bytes, "image/png")},
    )
    assert second.status_code == 429

    usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["used"] == 1
