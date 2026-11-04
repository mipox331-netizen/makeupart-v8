import hashlib
import json
from pathlib import Path

import pytest

from scripts import modal_volume_media_manifest as manifest


def test_manifest_captures_relative_paths_sizes_and_sha256(tmp_path):
    root = tmp_path / "media"
    photo = root / "salons" / "salon-a" / "after.png"
    logo = root / "salons" / "salon-a" / "logo.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"processed-photo")
    logo.write_bytes(b"salon-logo")
    output = tmp_path / "stage" / "manifest.json"

    count, total = manifest.build_manifest(root, output)

    assert count == 2
    assert total == len(b"processed-photo") + len(b"salon-logo")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["format"] == "makeupart-modal-volume-media-backup-v1"
    assert payload["file_count"] == 2
    assert payload["files"] == [
        {
            "path": "salons/salon-a/after.png",
            "size": len(b"processed-photo"),
            "sha256": hashlib.sha256(b"processed-photo").hexdigest(),
        },
        {
            "path": "salons/salon-a/logo.png",
            "size": len(b"salon-logo"),
            "sha256": hashlib.sha256(b"salon-logo").hexdigest(),
        },
    ]


def test_manifest_records_an_empty_volume_for_database_safety_check(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    output = tmp_path / "manifest.json"

    count, total = manifest.build_manifest(root, output)

    assert (count, total) == (0, 0)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["files"] == []
    assert payload["file_count"] == 0
    assert payload["total_bytes"] == 0


def test_manifest_rejects_symlinks(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    target = root / "photo.png"
    target.write_bytes(b"photo")
    (root / "linked.png").symlink_to(target)
    output = tmp_path / "manifest.json"

    with pytest.raises(manifest.MediaManifestError, match="Symbolic links"):
        manifest.build_manifest(root, output)


def test_manifest_rejects_empty_files(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    (root / "empty.png").write_bytes(b"")

    with pytest.raises(manifest.MediaManifestError, match="empty media object"):
        manifest.build_manifest(root, tmp_path / "manifest.json")


def test_manifest_rejects_files_over_limit(monkeypatch, tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    (root / "large.png").write_bytes(b"larger than allowed")
    monkeypatch.setattr(manifest, "MAX_FILE_BYTES", 4)

    with pytest.raises(manifest.MediaManifestError, match="512 MiB"):
        manifest.build_manifest(root, tmp_path / "manifest.json")


def test_manifest_requires_existing_download_directory(tmp_path):
    with pytest.raises(manifest.MediaManifestError, match="directory is missing"):
        manifest.build_manifest(tmp_path / "missing", tmp_path / "manifest.json")
