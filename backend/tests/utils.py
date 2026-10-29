PASSWORD = "password123"
API = "/api/v1"


def register(client, email="owner@salon.com", salon_name="Salon A", full_name="Owner One"):
    return client.post(
        f"{API}/auth/register",
        json={
            "salon_name": salon_name,
            "owner_full_name": full_name,
            "email": email,
            "password": PASSWORD,
        },
    )


def login(client, email, password=PASSWORD):
    return client.post(
        f"{API}/auth/login", data={"username": email, "password": password}
    )


def auth_headers(client, email):
    tokens = login(client, email).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def register_platform_admin(client, monkeypatch, email=None):
    """Provision a unique test admin before allowlisting its email.

    Public signup correctly refuses currently allowlisted admin addresses, so
    the test account is registered first and then promoted through the same
    settings allowlist used by the production dependency.
    """
    import uuid

    from app.core.config import settings

    email = email or f"platform-admin-{uuid.uuid4().hex}@salon.com"
    created = register(
        client,
        email=email,
        salon_name="Platform Admin Test Salon",
        full_name="Platform Admin Test",
    )
    assert created.status_code == 201, created.text
    monkeypatch.setattr(settings, "PLATFORM_ADMIN_EMAILS", email)
    response = login(client, email)
    assert response.status_code == 200, response.text
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_staff(client, headers, email="staff@salon.com", full_name="Staff One"):
    return client.post(
        f"{API}/users",
        headers=headers,
        json={"email": email, "full_name": full_name, "password": PASSWORD},
    )
