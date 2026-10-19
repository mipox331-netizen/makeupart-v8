import logging
from types import SimpleNamespace

from app.api.v1 import beauty as beauty_api


def test_generative_storage_readiness_fails_closed_and_logs_schema_error(monkeypatch, caplog):
    def broken_inspect(_bind):
        raise RuntimeError("database schema unavailable")

    monkeypatch.setattr(beauty_api, "inspect", broken_inspect)

    with caplog.at_level(logging.WARNING, logger="makeupart.beauty"):
        ready = beauty_api._generative_storage_ready(
            SimpleNamespace(get_bind=lambda: object())
        )

    assert ready is False
    assert "Generative storage readiness check failed (RuntimeError)." in caplog.text
