import hashlib
import json
from pathlib import Path

import pytest

from scripts import github_release_backup as backup


def make_archive(tmp_path: Path, name: str = "database.dump.gpg") -> tuple[Path, Path]:
    archive = tmp_path / name
    archive.write_bytes(b"encrypted test archive")
    checksum = Path(str(archive) + ".sha256")
    checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
    return archive, checksum


def test_local_archive_checksum_is_verified(tmp_path):
    archive, checksum = make_archive(tmp_path)
    size, digest = backup._verify_local_archive(archive, checksum)
    assert size == len(archive.read_bytes())
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_upload_rejects_checksum_mismatch_before_network_calls(tmp_path, monkeypatch):
    archive, checksum = make_archive(tmp_path)
    checksum.write_text("0" * 64 + f"  {archive.name}\n")
    called = []
    monkeypatch.setattr(backup, "_gh", lambda *args: called.append(args) or "true")

    with pytest.raises(backup.BackupStorageError, match="does not match"):
        backup.upload("database", archive, checksum, "12345-a1")

    assert called == []


def test_private_backup_repo_is_required(monkeypatch):
    monkeypatch.setenv("BACKUP_REPOSITORY", "owner/public-backups")
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/app")
    monkeypatch.setattr(backup, "_gh", lambda *args: "false")

    with pytest.raises(backup.BackupStorageError, match="must be private"):
        backup._ensure_private_target("owner/public-backups")


def test_backup_repository_must_be_separate(monkeypatch):
    monkeypatch.setenv("BACKUP_REPOSITORY", "owner/app")
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/app")

    with pytest.raises(backup.BackupStorageError, match="separate"):
        backup._backup_repository()


def test_download_rejects_bad_checksum_and_removes_archive(tmp_path, monkeypatch):
    archive, checksum = make_archive(tmp_path, "media.tar.gz.gpg")
    checksum.write_text("f" * 64 + f"  {archive.name}\n")
    monkeypatch.setenv("BACKUP_REPOSITORY", "owner/private-backups")
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/app")

    def fake_gh(*args):
        # Simulate gh release download: archive and checksum already exist in destination.
        assert args[0:3] == ("release", "download", "makeupart-media-12345-a1")
        assert Path(args[4]).name == "ignored"
        return ""

    monkeypatch.setattr(backup, "_gh", fake_gh)
    destination = tmp_path / "restore"
    destination.mkdir()
    # _gh receives --dir <destination>; create the files when download is invoked.
    original = backup._gh

    def fake_download(*args):
        dest = Path(args[args.index("--dir") + 1])
        dest.mkdir(parents=True, exist_ok=True)
        (dest / archive.name).write_bytes(archive.read_bytes())
        Path(dest / (archive.name + ".sha256")).write_text(checksum.read_text())
        return ""

    monkeypatch.setattr(backup, "_gh", fake_download)
    with pytest.raises(backup.BackupStorageError, match="does not match"):
        backup.download("media", "12345-a1", destination)
    assert not (destination / archive.name).exists()
