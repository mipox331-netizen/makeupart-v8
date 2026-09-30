from tests.utils import API, auth_headers, register


def test_customer_consent_lifecycle(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    customer = client.post(
        f"{API}/customers",
        headers=headers,
        json={"first_name": "Aisha", "last_name": "Kiboko", "consent_required": True},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    blocked = client.get(f"{API}/consents/customer/{customer_id}/active", headers=headers)
    assert blocked.status_code == 200
    assert blocked.json() is None

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
    assert granted.json()["granted"] is True

    active = client.get(f"{API}/consents/customer/{customer_id}/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["id"] == granted.json()["id"]

    revoked = client.post(
        f"{API}/consents",
        headers=headers,
        json={
            "customer_id": customer_id,
            "granted": False,
            "consent_text": "Client withdrew AI beauty processing consent.",
        },
    )
    assert revoked.status_code == 201
    assert client.get(
        f"{API}/consents/customer/{customer_id}/active", headers=headers
    ).json() is None


def test_cross_salon_consent_is_hidden(client):
    register(client, email="owner.a@salon.com", salon_name="Salon A")
    register(client, email="owner.b@salon.com", salon_name="Salon B")
    headers_a = auth_headers(client, "owner.a@salon.com")
    headers_b = auth_headers(client, "owner.b@salon.com")

    customer_a = client.post(
        f"{API}/customers",
        headers=headers_a,
        json={"first_name": "A", "last_name": "One"},
    ).json()["id"]

    assert client.post(
        f"{API}/consents",
        headers=headers_b,
        json={
            "customer_id": customer_a,
            "granted": True,
            "consent_text": "Should not be accepted.",
        },
    ).status_code == 404
