from tests.utils import API, PASSWORD, auth_headers, create_staff, login, register


def test_patch_me_persists(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.patch(
        f"{API}/users/me", headers=headers, json={"full_name": "New Name", "phone": "0700000000"}
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"

    again = client.get(f"{API}/users/me", headers=headers)
    assert again.json()["full_name"] == "New Name"
    assert again.json()["phone"] == "0700000000"


def test_owner_can_create_and_list_staff(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")

    created = create_staff(client, headers)
    assert created.status_code == 201
    assert created.json()["role"] == "staff"

    listing = client.get(f"{API}/users", headers=headers)
    assert listing.status_code == 200
    emails = {u["email"] for u in listing.json()}
    assert emails == {"owner@salon.com", "staff@salon.com"}


def test_staff_can_login_but_cannot_manage_users(client):
    register(client)
    owner_headers = auth_headers(client, "owner@salon.com")
    create_staff(client, owner_headers)

    assert login(client, "staff@salon.com").status_code == 200
    staff_headers = auth_headers(client, "staff@salon.com")

    assert client.get(f"{API}/users", headers=staff_headers).status_code == 403
    assert create_staff(client, staff_headers, email="x@salon.com").status_code == 403
    assert client.patch(
        f"{API}/salons/me", headers=staff_headers, json={"name": "Hacked"}
    ).status_code == 403


def test_staff_creation_rejects_duplicate_email(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    assert create_staff(client, headers).status_code == 201
    assert create_staff(client, headers).status_code == 409


def test_owner_can_delete_staff_but_not_self(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    staff = create_staff(client, headers).json()
    owner = client.get(f"{API}/users/me", headers=headers).json()

    assert client.delete(f"{API}/users/{owner['id']}", headers=headers).status_code == 400
    assert client.delete(f"{API}/users/{staff['id']}", headers=headers).status_code == 204
    assert login(client, "staff@salon.com").status_code == 401


def test_patch_salon_persists(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.patch(
        f"{API}/salons/me",
        headers=headers,
        json={"instagram": "@salon_a", "location": "Dar es Salaam"},
    )
    assert response.status_code == 200

    salon = client.get(f"{API}/salons/me", headers=headers).json()
    assert salon["instagram"] == "@salon_a"
    assert salon["location"] == "Dar es Salaam"
    assert salon["name"] == "Salon A"


def test_salons_are_isolated_from_each_other(client):
    register(client, email="owner.a@salon.com", salon_name="Salon A")
    register(client, email="owner.b@salon.com", salon_name="Salon B")
    headers_a = auth_headers(client, "owner.a@salon.com")
    headers_b = auth_headers(client, "owner.b@salon.com")

    staff_a = create_staff(client, headers_a, email="staff.a@salon.com").json()

    listing_b = client.get(f"{API}/users", headers=headers_b).json()
    assert {u["email"] for u in listing_b} == {"owner.b@salon.com"}

    assert client.delete(f"{API}/users/{staff_a['id']}", headers=headers_b).status_code == 404
    assert client.get(f"{API}/salons/me", headers=headers_b).json()["name"] == "Salon B"
    assert client.get(f"{API}/salons/me", headers=headers_a).json()["name"] == "Salon A"

    listing_a = client.get(f"{API}/users", headers=headers_a).json()
    assert {u["email"] for u in listing_a} == {"owner.a@salon.com", "staff.a@salon.com"}
