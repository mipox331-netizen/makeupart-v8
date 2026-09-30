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


def create_staff(client, headers, email="staff@salon.com", full_name="Staff One"):
    return client.post(
        f"{API}/users",
        headers=headers,
        json={"email": email, "full_name": full_name, "password": PASSWORD},
    )
