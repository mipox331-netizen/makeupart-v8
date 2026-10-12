from datetime import datetime, timezone

from app.core.config import settings
from tests.utils import API, auth_headers, register


def _register_platform_admin(client, monkeypatch, email="platform-admin@makeupart.local"):
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_EMAILS", email)
    register(client, email=email, salon_name="Platform Admin Salon", full_name="Platform Admin")
    return auth_headers(client, email)


def test_platform_admin_records_verified_payment_and_activates_plan(client, monkeypatch):
    owner_registration = register(client, email="revenue-owner@salon.com", salon_name="Revenue Salon")
    owner_headers = auth_headers(client, "revenue-owner@salon.com")
    salon = client.get(f"{API}/salons/me", headers=owner_headers)
    assert salon.status_code == 200
    salon_id = salon.json()["id"]

    admin_headers = _register_platform_admin(client, monkeypatch)
    response = client.post(
        f"{API}/admin/payments/record",
        headers=admin_headers,
        json={
            "salon_id": salon_id,
            "plan": "pro",
            "amount": "125000.00",
            "currency": "TZS",
            "payment_method": "mobile_money",
            "period_days": 365,
            "reference": "MOBILE-TX-0001",
            "notes": "Verified against mobile money receipt",
        },
    )

    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment["salon_id"] == salon_id
    assert payment["salon_name"] == "Revenue Salon"
    assert payment["plan"] == "pro"
    assert float(payment["amount"]) == 125000.0
    assert payment["currency"] == "TZS"
    assert payment["status"] == "confirmed"
    assert payment["period_days"] == 365
    assert payment["recorded_by_email"] == "platform-admin@makeupart.local"

    usage = client.get(f"{API}/subscriptions/me", headers=owner_headers)
    assert usage.status_code == 200
    assert usage.json()["plan"] == "pro"
    assert usage.json()["monthly_limit"] == 1000
    assert usage.json()["status"] == "active"
    assert usage.json()["current_period_end"] is not None

    summary = client.get(
        f"{API}/admin/payments/summary?period=year",
        headers=admin_headers,
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["period"] == "year"
    assert body["transaction_count"] == 1
    assert len(body["totals_by_currency"]) == 1
    assert body["totals_by_currency"][0]["currency"] == "TZS"
    assert body["totals_by_currency"][0]["transaction_count"] == 1
    assert float(body["totals_by_currency"][0]["collected_total"]) == 125000.0
    assert body["recent_payments"][0]["reference"] == "MOBILE-TX-0001"


def test_duplicate_payment_reference_is_rejected_without_second_activation(client, monkeypatch):
    register(client, email="repeat-owner@salon.com", salon_name="Repeat Salon")
    owner_headers = auth_headers(client, "repeat-owner@salon.com")
    salon_id = client.get(f"{API}/salons/me", headers=owner_headers).json()["id"]
    admin_headers = _register_platform_admin(client, monkeypatch)

    payload = {
        "salon_id": salon_id,
        "plan": "basic",
        "amount": "30000.00",
        "currency": "TZS",
        "payment_method": "mobile_money",
        "period_days": 30,
        "reference": "DUPLICATE-REF-77",
    }
    first = client.post(f"{API}/admin/payments/record", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    current_end = client.get(f"{API}/subscriptions/me", headers=owner_headers).json()["current_period_end"]

    second = client.post(f"{API}/admin/payments/record", headers=admin_headers, json=payload)
    assert second.status_code == 409, second.text
    assert "already been recorded" in second.json()["detail"]

    after = client.get(f"{API}/subscriptions/me", headers=owner_headers).json()
    assert after["current_period_end"] == current_end
    summary = client.get(
        f"{API}/admin/payments/summary?period=year",
        headers=admin_headers,
    ).json()
    assert summary["transaction_count"] == 1


def test_non_platform_admin_cannot_read_or_write_payment_ledger(client):
    register(client, email="ordinary-owner@salon.com")
    headers = auth_headers(client, "ordinary-owner@salon.com")

    summary = client.get(f"{API}/admin/payments/summary?period=month", headers=headers)
    assert summary.status_code == 403

    record = client.post(
        f"{API}/admin/payments/record",
        headers=headers,
        json={
            "salon_id": "00000000-0000-0000-0000-000000000001",
            "plan": "pro",
            "amount": "1.00",
            "currency": "TZS",
            "payment_method": "cash",
            "period_days": 30,
        },
    )
    assert record.status_code == 403


def test_payment_schema_rejects_non_positive_amounts_and_free_plan(client, monkeypatch):
    admin_headers = _register_platform_admin(client, monkeypatch)
    register(client, email="billing-owner@salon.com")
    owner_headers = auth_headers(client, "billing-owner@salon.com")
    salon_id = client.get(f"{API}/salons/me", headers=owner_headers).json()["id"]

    payload = {
        "salon_id": salon_id,
        "plan": "pro",
        "amount": "0",
        "currency": "TZS",
        "payment_method": "manual",
        "period_days": 30,
    }
    zero = client.post(f"{API}/admin/payments/record", headers=admin_headers, json=payload)
    assert zero.status_code == 422

    payload["amount"] = "1000.00"
    payload["plan"] = "free"
    free = client.post(f"{API}/admin/payments/record", headers=admin_headers, json=payload)
    assert free.status_code == 422
