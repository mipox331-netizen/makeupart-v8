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


def test_api_readiness_does_not_depend_on_drive_oauth(client, monkeypatch):
    import app.main as main_module
    from app.core.config import settings
    from app.services.google_drive_media import GoogleDriveMediaError

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, statement):
            return None

    monkeypatch.setattr(main_module.engine, "connect", lambda: FakeConnection())
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setattr(
        main_module.google_drive_media,
        "verify_connection",
        lambda: (_ for _ in ()).throw(GoogleDriveMediaError("Drive unavailable")),
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_production_media_readiness_fails_closed_without_drive_oauth(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")

    response = client.get("/health/media-ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "media_storage_unavailable",
    }


def test_media_readiness_requires_successful_drive_verification(client, monkeypatch):
    import app.main as main_module
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", True)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(main_module.google_drive_media, "verify_connection", lambda: None)

    response = client.get("/health/media-ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "storage": "google_drive"}


def test_local_media_readiness_reports_local_only_mode(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")

    response = client.get("/health/media-ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "storage": "local_only"}


def test_readiness_reports_running_render_commit(client, monkeypatch):
    import app.main as main_module
    from app.core.config import settings

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, statement):
            return None

    monkeypatch.setattr(main_module.engine, "connect", lambda: FakeConnection())
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "REQUIRE_DURABLE_MEDIA", False)
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_REFRESH_TOKEN", "")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "test-deployment-commit")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "deployment_commit": "test-deployment-commit",
    }
