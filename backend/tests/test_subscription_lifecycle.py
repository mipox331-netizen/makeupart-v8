from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services import subscription as subscription_service
from tests.utils import API, auth_headers, register


def test_subscription_expiry_suspends_without_deleting_access(client, monkeypatch):
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_EMAILS", "owner@salon.com")
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")

    initial = client.get(f"{API}/subscriptions/me", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["status"] == "trialing"

    activated = client.post(
        f"{API}/admin/subscriptions/{registration.json()['salon']['id']}/activate",
        headers=headers,
        json={"plan": "pro", "days": 1},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    expired_now = datetime.now(timezone.utc) + timedelta(days=2)
    monkeypatch.setattr(subscription_service, "_now", lambda: expired_now)

    snapshot = client.get(f"{API}/subscriptions/me", headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["status"] == "suspended"
    assert snapshot.json()["plan"] == "pro"

    rows = client.get(f"{API}/admin/subscriptions", headers=headers)
    assert rows.status_code == 200
    assert rows.json()[0]["status"] == "suspended"


def test_platform_admin_can_reactivate_suspended_salon(client, monkeypatch):
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_EMAILS", "owner@salon.com")
    registration = register(client)
    headers = auth_headers(client, "owner@salon.com")
    salon_id = registration.json()["salon"]["id"]

    suspended = client.post(
        f"{API}/admin/subscriptions/{salon_id}/suspend",
        headers=headers,
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    reactivated = client.post(
        f"{API}/admin/subscriptions/{salon_id}/activate",
        headers=headers,
        json={"plan": "basic", "days": 30},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"
    assert reactivated.json()["plan"] == "basic"

    snapshot = client.get(f"{API}/subscriptions/me", headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["status"] == "active"


def test_non_platform_admin_cannot_manage_subscriptions(client, monkeypatch):
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_EMAILS", "owner@salon.com")
    register(client)
    other = register(client, email="other@salon.com", salon_name="Other Salon")
    other_headers = auth_headers(client, "other@salon.com")
    assert other.status_code == 201

    response = client.get(f"{API}/admin/subscriptions", headers=other_headers)
    assert response.status_code == 403
