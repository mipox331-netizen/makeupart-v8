from tests.utils import API, auth_headers, register


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
