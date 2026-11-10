from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import r2_backup_storage as storage


class FakePaginator:
    def __init__(self, client):
        self.client = client

    def paginate(self, Bucket, Prefix):
        yield {
            "Contents": [
                {"Key": key, "Size": len(value), "LastModified": datetime.now(timezone.utc)}
                for key, value in self.client.objects.items()
                if key.startswith(Prefix)
            ]
        }


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.metadata = {}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return FakePaginator(self)

    def upload_file(self, filename, bucket, key, ExtraArgs):
        body = Path(filename).read_bytes()
        self.objects[key] = body
        self.metadata[key] = ExtraArgs["Metadata"]

    def put_object(self, Bucket, Key, Body, ContentLength, ContentType, Metadata):
        body = Body.read()
        assert len(body) == ContentLength
        self.objects[Key] = body
        self.metadata[Key] = Metadata

    def head_object(self, Bucket, Key):
        return {
            "ContentLength": len(self.objects[Key]),
            "Metadata": self.metadata[Key],
        }

    def download_file(self, Bucket, Key, filename):
        Path(filename).write_bytes(self.objects[Key])

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)
        self.metadata.pop(Key, None)


@pytest.fixture
def fake_r2(monkeypatch):
    client = FakeR2()
    monkeypatch.setattr(storage, "_bucket", lambda: "private-backups")
    monkeypatch.setattr(storage, "_client", lambda: client)
    return client


def test_upload_verifies_encrypted_archive_and_sidecar(fake_r2, tmp_path):
    archive = tmp_path / "db.dump.gpg"
    archive.write_bytes(b"encrypted-database-archive")
    checksum = tmp_path / "db.dump.gpg.sha256"
    checksum.write_text(f"{storage._sha256(archive)[1]}  db.dump.gpg\n")

    archive_key, checksum_key = storage.upload(
        "database", archive, checksum, "12345-a1"
    )

    assert archive_key == "makeupart-backups/database/12345-a1/db.dump.gpg"
    assert checksum_key == archive_key + ".sha256"
    assert fake_r2.objects[archive_key] == archive.read_bytes()
    assert fake_r2.metadata[archive_key]["encryption"] == "client-side-gpg-aes256"


def test_upload_rejects_checksum_mismatch(fake_r2, tmp_path):
    archive = tmp_path / "media.tar.gz.gpg"
    archive.write_bytes(b"encrypted-media-archive")
    checksum = tmp_path / "media.tar.gz.gpg.sha256"
    checksum.write_text("0" * 64 + "  media.tar.gz.gpg\n")

    with pytest.raises(storage.BackupStorageError, match="does not match"):
        storage.upload("media", archive, checksum, "12345-a1")


def test_download_verifies_archive_before_returning(fake_r2, tmp_path):
    archive = tmp_path / "media.tar.gz.gpg"
    archive.write_bytes(b"encrypted-media-archive")
    checksum = tmp_path / "media.tar.gz.gpg.sha256"
    checksum.write_text(f"{storage._sha256(archive)[1]}  media.tar.gz.gpg\n")
    storage.upload("media", archive, checksum, "12345-a1")

    destination = tmp_path / "restore"
    restored = storage.download("media", "12345-a1", destination)

    assert restored.read_bytes() == archive.read_bytes()
    assert Path(str(restored) + ".sha256").is_file()


def test_download_deletes_archive_when_checksum_is_wrong(fake_r2, tmp_path):
    key = "makeupart-backups/database/12345-a1/db.dump.gpg"
    fake_r2.objects[key] = b"altered-encrypted-archive"
    fake_r2.objects[key + ".sha256"] = (("0" * 64) + "  db.dump.gpg\n").encode()

    with pytest.raises(storage.BackupStorageError, match="failed SHA-256"):
        storage.download("database", "12345-a1", tmp_path / "restore")

    assert not (tmp_path / "restore/db.dump.gpg").exists()


def test_upload_refuses_to_exceed_free_storage_safety_ceiling(fake_r2, tmp_path, monkeypatch):
    fake_r2.objects["makeupart-backups/media/old/object.bin"] = b"x" * 100
    monkeypatch.setattr(storage, "MAX_STORED_BYTES", 10)
    archive = tmp_path / "db.dump.gpg"
    archive.write_bytes(b"123456789")
    checksum = tmp_path / "db.dump.gpg.sha256"
    checksum.write_text(f"{storage._sha256(archive)[1]}  db.dump.gpg\n")

    with pytest.raises(storage.BackupStorageError, match="9.5 GB safety ceiling"):
        storage.upload("database", archive, checksum, "12345-a1")
