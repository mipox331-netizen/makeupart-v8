from datetime import datetime, timedelta, timezone

from app.models.salon import SubscriptionPlan
from app.models.subscription import Subscription
from app.services import subscription as subscription_service
from tests.utils import API, auth_headers, register, register_platform_admin


def test_subscription_usage_defaults_to_permanent_free(client):
    register(client)
    response = client.get(f"{API}/subscriptions/me", headers=auth_headers(client, "owner@salon.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["status"] == "active"
    assert body["monthly_limit"] == 25
    assert body["used"] == 0
    assert body["remaining"] == 25
    assert body["current_period_end"] is None


def test_first_subscription_creation_is_reused_instead_of_duplicated():
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base
    from app.models.salon import Salon

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            salon = Salon(name="First Use Salon", email="first-use@example.com")
            session.add(salon)
            session.flush()

            first = subscription_service._get_subscription(session, salon.id, lock=False)
            first_id = first.id
            session.commit()

            second = subscription_service._get_subscription(session, salon.id, lock=True)
            assert second.id == first_id

            rows = session.execute(
                select(Subscription.id).where(Subscription.salon_id == salon.id)
            ).scalars().all()
            assert rows == [first_id]
            session.commit()
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


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


def test_subscription_service_expires_due_subscription():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        from app.models.salon import Salon
        salon = Salon(name="Expiry Salon", email="expiry@example.com")
        session.add(salon)
        session.flush()
        subscription = Subscription(
            salon_id=salon.id,
            plan="basic",
            status="active",
            current_period_end=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        session.add(subscription)
        session.commit()

        subscription_service._expire_if_due(subscription)
        assert subscription.status == "suspended"

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_expired_free_trial_is_normalised_to_active():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        from app.models.salon import Salon

        salon = Salon(name="Legacy Free Salon")
        session.add(salon)
        session.flush()
        subscription = Subscription(
            salon_id=salon.id,
            plan="free",
            status="trialing",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=10),
        )
        session.add(subscription)
        session.commit()

        changed = subscription_service._expire_if_due(subscription)
        assert changed is True
        assert subscription.status == "active"
        assert subscription.current_period_end is None

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_suspended_free_plan_is_reopened():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        from app.models.salon import Salon

        salon = Salon(name="Suspended Free Salon")
        session.add(salon)
        session.flush()
        subscription = Subscription(
            salon_id=salon.id,
            plan="free",
            status="suspended",
            current_period_end=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(subscription)
        session.commit()

        changed = subscription_service._expire_if_due(subscription)
        assert changed is True
        assert subscription.status == "active"
        assert subscription.current_period_end is None

    Base.metadata.drop_all(bind=engine)
    engine.dispose()

def test_free_plan_exposes_only_free_makeup_and_photo_finish_entitlements(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.get(f"{API}/subscriptions/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["available_makeup_styles"] == ["natural"]
    assert body["available_photo_finishes"] == ["Natural Finish", "Warm Glow"]


def test_free_plan_cannot_bypass_premium_makeup_style_gate(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    response = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&makeup_style=soft_glam",
        headers=headers,
        files={"file": ("portrait.png", b"invalid image", "image/png")},
    )
    assert response.status_code == 403
    assert response.headers["X-Required-Plan"] == "basic"
    assert "Basic plan or higher" in response.json()["detail"]

    usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["used"] == 0


def test_free_plan_cannot_bypass_pro_photo_finish_gate(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    response = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&photo_finish=Studio%20Polish",
        headers=headers,
        files={"file": ("portrait.png", b"invalid image", "image/png")},
    )
    assert response.status_code == 403
    assert response.headers["X-Required-Plan"] == "pro"
    assert "Pro plan or higher" in response.json()["detail"]

    usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["used"] == 0


def test_basic_plan_accepts_basic_style_and_finish_but_still_validates_image(client, monkeypatch):
    _, admin_headers = register_platform_admin(client, monkeypatch)

    register(client, email="basic-owner@salon.com", salon_name="Basic Salon")
    owner_headers = auth_headers(client, "basic-owner@salon.com")
    salon_id = client.get(f"{API}/salons/me", headers=owner_headers).json()["id"]
    activated = client.post(
        f"{API}/admin/subscriptions/{salon_id}/activate",
        headers=admin_headers,
        json={"plan": "basic", "days": 30},
    )
    assert activated.status_code == 200, activated.text

    response = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&makeup_style=soft_glam&photo_finish=Soft%20Glam",
        headers=owner_headers,
        files={"file": ("portrait.png", b"invalid image", "image/png")},
    )
    # Entitlement checks pass for Basic; invalid image input is rejected next.
    assert response.status_code == 422, response.text
    assert "valid image" in response.json()["detail"].lower()

    usage = client.get(f"{API}/subscriptions/me", headers=owner_headers)
    assert usage.status_code == 200
    assert usage.json()["used"] == 0

def test_free_plan_cannot_bypass_paid_generative_engine_gate(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    response = client.post(
        f"{API}/beauty/process-upload?consent_confirmed=true&engine=generative&external_ai_consent=true",
        headers=headers,
        files={"file": ("portrait.png", b"invalid image", "image/png")},
    )
    assert response.status_code == 403
    assert response.headers["X-Required-Plan"] == "pro"
    assert "Pro plan or higher" in response.json()["detail"]

    usage = client.get(f"{API}/subscriptions/me", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["used"] == 0
    assert usage.json()["generative_engine_entitled"] is False

