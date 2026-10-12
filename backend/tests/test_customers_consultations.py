import pytest
from fastapi import HTTPException
from pathlib import Path
from types import SimpleNamespace
import uuid

from app.api.v1 import consultations as consultations_api
from app.api.v1 import customers as customers_api
from tests.utils import API, auth_headers, register


def test_customer_consent_cannot_be_disabled_via_api(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    created = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Consent", "last_name": "Protected", "consent_required": False},
    )
    assert created.status_code == 422

    normal = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Consent", "last_name": "Protected"},
    )
    assert normal.status_code == 201
    customer_id = normal.json()["id"]

    patched = client.patch(
        f"{API}/customers/{customer_id}",
        headers=headers,
        json={"consent_required": False},
    )
    assert patched.status_code == 422
    assert client.get(f"{API}/customers/{customer_id}", headers=headers).json()["consent_required"] is True


def test_legacy_customer_flag_cannot_bypass_consultation_consent(client, monkeypatch):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    customer = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Legacy", "last_name": "Client"},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    original_get_customer = consultations_api.get_customer

    def legacy_customer(db, requested_id):
        row = original_get_customer(db, requested_id)
        if row is not None:
            row.consent_required = False
        return row

    monkeypatch.setattr(consultations_api, "get_customer", legacy_customer)
    response = client.post(
        f"{API}/consultations",
        headers=headers,
        json={
            "customer_id": customer_id,
            "selected_makeup": "Natural Glow",
            "shade": "Medium Warm",
            "consent_granted": True,
        },
    )
    assert response.status_code == 403
    assert "Active customer consent" in response.json()["detail"]


def test_privacy_delete_does_not_report_success_when_media_removal_fails(monkeypatch, tmp_path):
    salon_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    media_root = tmp_path / "media"
    candidate = media_root / "salons" / str(salon_id) / "inputs" / "portrait.png"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(b"private-image")
    monkeypatch.setattr(customers_api.settings, "MEDIA_ROOT", str(media_root))

    class FakeRows:
        def scalars(self):
            return self
        def all(self):
            return [SimpleNamespace(input_file_path=str(candidate), output_file_path=None)]

    class FakeDb:
        def execute(self, _statement):
            return FakeRows()

    original_unlink = Path.unlink

    def fail_target_unlink(path, *args, **kwargs):
        if path.resolve() == candidate.resolve():
            raise PermissionError("simulated filesystem denial")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_target_unlink)
    with pytest.raises(HTTPException) as exc:
        customers_api._delete_customer_media(FakeDb(), salon_id, customer_id)

    assert exc.value.status_code == 500
    assert "records were retained" in exc.value.detail
    assert candidate.exists()


def test_customer_and_consultation_are_salon_scoped(client):
    register(client, email='owner.a@salon.com', salon_name='Salon A')
    register(client, email='owner.b@salon.com', salon_name='Salon B')
    headers_a = auth_headers(client, 'owner.a@salon.com')
    headers_b = auth_headers(client, 'owner.b@salon.com')

    customer_a = client.post(
        f'{API}/customers',
        headers=headers_a,
        json={'first_name': 'Aisha', 'last_name': 'Kiboko', 'consent_required': True},
    )
    assert customer_a.status_code == 201
    customer_a_id = customer_a.json()['id']

    customer_b = client.post(
        f'{API}/customers',
        headers=headers_b,
        json={'first_name': 'Bibi', 'last_name': 'Kazi', 'consent_required': True},
    )
    assert customer_b.status_code == 201

    listing_a = client.get(f'{API}/customers', headers=headers_a)
    listing_b = client.get(f'{API}/customers', headers=headers_b)
    assert len(listing_a.json()) == 1
    assert len(listing_b.json()) == 1
    assert listing_a.json()[0]['first_name'] == 'Aisha'
    assert listing_b.json()[0]['first_name'] == 'Bibi'

    consent = client.post(
        f"{API}/consents",
        headers=headers_a,
        json={
            "customer_id": customer_a_id,
            "granted": True,
            "consent_text": "Client consented to consultation and AI beauty processing.",
        },
    )
    assert consent.status_code == 201

    consultation = client.post(
        f'{API}/consultations',
        headers=headers_a,
        json={
            'customer_id': customer_a_id,
            'selected_makeup': 'Natural Glow',
            'shade': 'Medium Warm',
            'intensity': 0.8,
            'consent_granted': True,
        },
    )
    assert consultation.status_code == 201
    assert consultation.json()['salon_id'] == client.get(f'{API}/salons/me', headers=headers_a).json()['id']

    assert client.get(f'{API}/customers/{customer_b.json()["id"]}', headers=headers_a).status_code == 404
    assert client.get(f'{API}/consultations/{consultation.json()["id"]}', headers=headers_b).status_code == 404


def test_owner_can_privacy_delete_customer(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    created = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Delete", "last_name": "Me", "consent_required": True},
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    deleted = client.delete(f"{API}/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"{API}/customers/{customer_id}", headers=headers).status_code == 404
    assert client.get(
        f"{API}/consents/customer/{customer_id}/active", headers=headers
    ).status_code == 404


def test_customer_optional_fields_can_be_cleared(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    created = client.post(
        f"{API}/customers",
        headers=headers,
        json={
            "first_name": "Clear",
            "last_name": "Fields",
            "phone": "0700000000",
            "notes": "remove me",
        },
    )
    assert created.status_code == 201
    customer_id = created.json()["id"]

    updated = client.patch(
        f"{API}/customers/{customer_id}",
        headers=headers,
        json={"phone": None, "notes": None},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] is None
    assert updated.json()["notes"] is None
