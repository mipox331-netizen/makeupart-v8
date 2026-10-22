from app.main import app


def test_unhandled_server_error_keeps_trace_id_and_security_headers(client):
    @app.get("/__tests__/unhandled-error", include_in_schema=False)
    def raise_unhandled_error():
        raise RuntimeError("expected test-only failure")

    added_route = app.router.routes[-1]
    try:
        response = client.get(
            "/__tests__/unhandled-error",
            headers={"X-Request-ID": "test-makeupart-request-id"},
        )
    finally:
        app.router.routes.remove(added_route)

    assert response.status_code == 500
    assert response.json()["request_id"] == "test-makeupart-request-id"
    assert response.headers["X-Request-ID"] == "test-makeupart-request-id"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_oversized_request_id_is_replaced_with_safe_trace_id(client):
    @app.get("/__tests__/oversized-request-id", include_in_schema=False)
    def raise_error_for_invalid_request_id():
        raise RuntimeError("expected test-only failure")

    added_route = app.router.routes[-1]
    untrusted_request_id = "x" * 2048
    try:
        response = client.get(
            "/__tests__/oversized-request-id",
            headers={"X-Request-ID": untrusted_request_id},
        )
    finally:
        app.router.routes.remove(added_route)

    assert response.status_code == 500
    response_request_id = response.headers["X-Request-ID"]
    assert response_request_id != untrusted_request_id
    assert len(response_request_id) <= 128
    assert response.json()["request_id"] == response_request_id


def test_production_readiness_fails_when_drive_is_missing_even_if_flag_is_false(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "media_storage_unavailable",
    }


def test_readiness_fails_closed_when_durable_drive_storage_is_required(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "media_storage_unavailable",
    }
