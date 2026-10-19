from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import uuid

from app.core.config import settings
from scripts import cleanup as cleanup_script


class FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _statement):
        return FakeScalars(self.rows)


def test_cleanup_expires_drive_media_when_render_local_root_is_missing(monkeypatch, tmp_path):
    media_root = tmp_path / "missing-media-root"
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(media_root))
    salon_id = uuid.uuid4()
    missing_file = (
        media_root / "salons" / str(salon_id) / "outputs" / "old-photo.png"
    )
    old_job = SimpleNamespace(
        salon_id=salon_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
        input_file_path=str(missing_file),
        output_file_path=None,
    )
    monkeypatch.setattr(
        cleanup_script, "SessionLocal", lambda: FakeSession([old_job])
    )
    deleted: list[Path] = []

    def delete_drive_media(path):
        deleted.append(Path(path))
        return True

    monkeypatch.setattr(
        cleanup_script.google_drive_media, "delete_media_file", delete_drive_media
    )

    # The Render local filesystem can disappear on restart, but old database
    # rows must still drive deletion of remote-only Drive objects.
    assert not media_root.exists()
    assert cleanup_script.cleanup_media() == 0
    assert deleted == [missing_file]
