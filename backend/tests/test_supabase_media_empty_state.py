import json
from pathlib import Path

import pytest

from scripts import verify_supabase_media_empty_state as verifier


class FakeResult:
    def __init__(self, scalar=None, rows=None):
        self.value = scalar
        self.rows = rows or []

    def scalar_one(self):
        return self.value

    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, revision="0014_beauty_media_paths", reference_count=0, missing_columns=None):
        self.revision = revision
        self.reference_count = reference_count
        all_columns = set(verifier.REQUIRED_MEDIA_COLUMNS)
        for item in missing_columns or set():
            all_columns.discard(item)
        self.columns = sorted(all_columns)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement, params=None):
        sql = str(statement)
        if "alembic_version" in sql:
            return FakeResult(scalar=self.revision)
        if "information_schema.columns" in sql:
            return FakeResult(rows=self.columns)
        if "SELECT" in sql and "beauty_jobs" in sql and "watermarks" in sql:
            return FakeResult(scalar=self.reference_count)
        raise AssertionError(f"Unexpected inventory SQL: {sql}")


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection
        self.disposed = False

    def connect(self):
        return self.connection

    def dispose(self):
        self.disposed = True


def write_manifest(tmp_path: Path, *, count=0, total=0, files=None):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps({
            "format": "makeupart-supabase-storage-media-backup-v1",
            "file_count": count,
            "total_bytes": total,
            "files": files or [],
        }),
        encoding="utf-8",
    )
    return path


def test_non_empty_media_manifest_does_not_require_empty_state_db_probe(
    monkeypatch, tmp_path
):
    manifest = write_manifest(
        tmp_path,
        count=1,
        total=4,
        files=[{"path": "salons/salon/photo.png", "size": 4, "sha256": "a" * 64}],
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def unexpected_engine(*args, **kwargs):
        raise AssertionError("Non-empty media should not need the empty-state database probe.")

    monkeypatch.setattr(verifier, "create_engine", unexpected_engine)

    assert verifier.verify_empty_media_inventory(manifest) == 1


def test_empty_media_manifest_passes_only_when_db_has_zero_media_references(
    monkeypatch, tmp_path
):
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://test@localhost/database")
    engine = FakeEngine(FakeConnection(reference_count=0))
    monkeypatch.setattr(verifier, "create_engine", lambda *args, **kwargs: engine)

    assert verifier.verify_empty_media_inventory(manifest) == 0
    assert engine.disposed is True


def test_empty_media_manifest_fails_when_db_references_customer_media(
    monkeypatch, tmp_path
):
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://test@localhost/database")
    engine = FakeEngine(FakeConnection(reference_count=2))
    monkeypatch.setattr(verifier, "create_engine", lambda *args, **kwargs: engine)

    with pytest.raises(verifier.MediaInventoryError, match="still references customer photos"):
        verifier.verify_empty_media_inventory(manifest)

    assert engine.disposed is True


def test_empty_media_manifest_fails_when_migration_head_is_stale(
    monkeypatch, tmp_path
):
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://test@localhost/database")
    engine = FakeEngine(FakeConnection(revision="0013_watermark_content"))
    monkeypatch.setattr(verifier, "create_engine", lambda *args, **kwargs: engine)

    with pytest.raises(verifier.MediaInventoryError, match="migration head"):
        verifier.verify_empty_media_inventory(manifest)

    assert engine.disposed is True


def test_empty_media_manifest_fails_when_media_columns_are_missing(
    monkeypatch, tmp_path
):
    manifest = write_manifest(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://test@localhost/database")
    engine = FakeEngine(FakeConnection(missing_columns={("beauty_jobs", "input_file_path")}))
    monkeypatch.setattr(verifier, "create_engine", lambda *args, **kwargs: engine)

    with pytest.raises(verifier.MediaInventoryError, match="columns are missing"):
        verifier.verify_empty_media_inventory(manifest)

    assert engine.disposed is True
