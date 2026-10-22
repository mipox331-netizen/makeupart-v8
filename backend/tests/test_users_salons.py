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


def test_profile_patch_rejects_null_non_nullable_name(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    before = client.get(f"{API}/users/me", headers=headers).json()

    response = client.patch(f"{API}/users/me", headers=headers, json={"full_name": None})
    assert response.status_code == 422
    after = client.get(f"{API}/users/me", headers=headers).json()
    assert after["full_name"] == before["full_name"]


def test_salon_patch_rejects_null_name(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    before = client.get(f"{API}/salons/me", headers=headers).json()

    response = client.patch(f"{API}/salons/me", headers=headers, json={"name": None})
    assert response.status_code == 422
    after = client.get(f"{API}/salons/me", headers=headers).json()
    assert after["name"] == before["name"]


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


def test_staff_creation_rejects_password_over_bcrypt_utf8_byte_limit(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.post(
        f"{API}/users",
        headers=headers,
        json={
            "email": "long-password-staff@salon.com",
            "full_name": "Staff Member",
            "password": "é" * 37,
        },
    )
    assert response.status_code == 422


def test_staff_creation_rejects_duplicate_email(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    assert create_staff(client, headers).status_code == 201
    assert create_staff(client, headers).status_code == 409


def test_staff_creation_race_returns_conflict_not_500(client, monkeypatch):
    import app.api.v1.users as users_api

    register(client)
    headers = auth_headers(client, "owner@salon.com")
    existing = create_staff(client, headers, email="race@salon.com")
    assert existing.status_code == 201

    original_lookup = users_api.get_user_by_email
    calls = 0

    def hide_existing_on_precheck(db, email):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return original_lookup(db, email)

    monkeypatch.setattr(users_api, "get_user_by_email", hide_existing_on_precheck)
    response = client.post(
        f"{API}/users",
        headers=headers,
        json={
            "email": "race@salon.com",
            "full_name": "Racing Staff",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already in use"


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


def test_owner_delete_protection_remains_enforced(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    owner = client.get(f"{API}/users/me", headers=headers).json()
    response = client.delete(f"{API}/users/{owner['id']}", headers=headers)
    assert response.status_code == 400


def test_platform_admin_can_list_and_block_users(client, monkeypatch):
    register(client)
    monkeypatch.setattr("app.core.config.settings.PLATFORM_ADMIN_EMAILS", "owner@salon.com")
    other = register(client, email="other@salon.com", salon_name="Other Salon")
    admin_headers = auth_headers(client, "owner@salon.com")
    other_tokens = login(client, "other@salon.com").json()
    other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
    old_refresh_token = other_tokens["refresh_token"]
    other_id = other.json()["user"]["id"]

    listing = client.get(f"{API}/admin/users", headers=admin_headers)
    assert listing.status_code == 200
    listed = {row["email"]: row for row in listing.json()}
    assert set(listed) == {"owner@salon.com", "other@salon.com"}
    assert listed["other@salon.com"]["is_active"] is True

    blocked = client.patch(
        f"{API}/admin/users/{other_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert blocked.status_code == 200
    assert blocked.json()["is_active"] is False

    assert client.get(f"{API}/users/me", headers=other_headers).status_code == 403
    assert login(client, "other@salon.com").status_code == 403

    unblocked = client.patch(
        f"{API}/admin/users/{other_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert unblocked.status_code == 200
    assert unblocked.json()["is_active"] is True

    # Old access and refresh tokens must not become valid again after unblock.
    assert client.get(f"{API}/users/me", headers=other_headers).status_code == 401
    assert client.post(
        f"{API}/auth/refresh", json={"refresh_token": old_refresh_token}
    ).status_code == 401
    assert login(client, "other@salon.com").status_code == 200


def test_non_platform_admin_cannot_manage_platform_users(client, monkeypatch):
    register(client)
    monkeypatch.setattr("app.core.config.settings.PLATFORM_ADMIN_EMAILS", "owner@salon.com")
    register(client, email="other@salon.com", salon_name="Other Salon")
    headers = auth_headers(client, "other@salon.com")
    assert client.get(f"{API}/admin/users", headers=headers).status_code == 403
