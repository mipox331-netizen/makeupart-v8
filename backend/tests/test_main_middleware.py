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
