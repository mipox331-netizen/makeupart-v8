from tests.utils import API, PASSWORD, auth_headers, login, register


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_register_creates_salon_and_owner(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "owner"
    assert body["user"]["salon_id"] == body["salon"]["id"]
    assert body["salon"]["name"] == "Salon A"
    assert body["salon"]["subscription_plan"] == "free"


def test_register_rejects_duplicate_email_case_insensitive(client):
    assert register(client, email="owner@salon.com").status_code == 201
    assert register(client, email="OWNER@salon.com").status_code == 409


def test_register_race_returns_conflict_instead_of_server_error(client, monkeypatch):
    from app.api.v1 import auth as auth_api

    email = "registration-race@salon.com"
    assert register(client, email=email, salon_name="Existing Salon").status_code == 201

    original_lookup = auth_api.get_user_by_email
    calls = 0

    def hide_existing_user_on_precheck(db, candidate_email):
        nonlocal calls
        calls += 1
        if calls == 1:
            # Simulate another request inserting this address after our initial read.
            return None
        return original_lookup(db, candidate_email)

    monkeypatch.setattr(auth_api, "get_user_by_email", hide_existing_user_on_precheck)
    response = client.post(
        f"{API}/auth/register",
        json={
            "salon_name": "Competing Salon",
            "owner_full_name": "Competing Owner",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_register_rejects_short_password(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "salon_name": "Salon",
            "owner_full_name": "Owner",
            "email": "a@b.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


def test_register_rejects_password_over_bcrypt_utf8_byte_limit(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "salon_name": "Salon",
            "owner_full_name": "Owner",
            "email": "long-password@salon.com",
            "password": "é" * 37,
        },
    )
    assert response.status_code == 422


def test_login_success(client):
    register(client)
    response = login(client, "owner@salon.com")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password(client):
    register(client)
    assert login(client, "owner@salon.com", "wrong-password").status_code == 401


def test_login_unknown_user(client):
    assert login(client, "nobody@salon.com").status_code == 401


def test_login_locks_email_after_five_failed_attempts(client):
    register(client, email="locked@salon.com")
    for _ in range(5):
        assert login(client, "locked@salon.com", "wrong-password").status_code == 401

    response = login(client, "locked@salon.com", PASSWORD)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "900"
    assert "Too many failed login attempts" in response.json()["detail"]


def test_successful_login_clears_previous_failures(client):
    register(client, email="recover@salon.com")
    for _ in range(3):
        assert login(client, "recover@salon.com", "wrong-password").status_code == 401

    assert login(client, "recover@salon.com", PASSWORD).status_code == 200
    for _ in range(4):
        assert login(client, "recover@salon.com", "wrong-password").status_code == 401


def test_me_requires_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401


def test_me_returns_current_user(client):
    register(client)
    headers = auth_headers(client, "owner@salon.com")
    response = client.get(f"{API}/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "owner@salon.com"


def test_refresh_returns_new_tokens(client):
    register(client)
    refresh = login(client, "owner@salon.com").json()["refresh_token"]
    response = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    new_tokens = response.json()
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
    assert me.status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_refresh_rejects_access_token(client):
    register(client)
    access = login(client, "owner@salon.com").json()["access_token"]
    response = client.post(f"{API}/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client):
    register(client)
    refresh = login(client, "owner@salon.com").json()["refresh_token"]
    response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


def test_garbage_token_rejected(client):
    response = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_logout_revokes_refresh_and_access_tokens(client):
    register(client)
    tokens = login(client, "owner@salon.com")
    refresh = tokens["refresh_token"]
    access = tokens["access_token"]

    response = client.post(f"{API}/auth/logout", json={"refresh_token": refresh})
    assert response.status_code == 204
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    assert client.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    ).status_code == 401
