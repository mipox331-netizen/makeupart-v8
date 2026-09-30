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


def test_logout_revokes_refresh_token(client):
    register(client)
    refresh = login(client, "owner@salon.com").json()["refresh_token"]
    response = client.post(f"{API}/auth/logout", json={"refresh_token": refresh})
    assert response.status_code == 204
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": refresh}).status_code == 401
