import hashlib

import pytest
import requests

from scripts import google_drive_backup_upload as uploader


class FakeResponse:
    def __init__(self, status_code=200, chunks=()):
        self.status_code = status_code
        self._chunks = chunks
        self.closed = False

    def iter_content(self, chunk_size):
        assert chunk_size == 1024 * 1024
        yield from self._chunks

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_drive_read_back_verifies_actual_bytes_and_closes_response():
    payload = b"encrypted backup bytes"
    response = FakeResponse(chunks=[payload[:8], b"", payload[8:]])
    session = FakeSession(response=response)
    expected_md5 = hashlib.md5(payload, usedforsecurity=False).hexdigest()

    uploader.verify_drive_file_bytes(
        session,
        {"Authorization": "Bearer test-token"},
        "private-file-id",
        len(payload),
        expected_md5,
    )

    assert response.closed is True
    assert session.calls[0][0].endswith("/files/private-file-id")
    assert session.calls[0][1]["params"] == {"alt": "media"}
    assert session.calls[0][1]["stream"] is True


def test_drive_read_back_rejects_checksum_mismatch():
    response = FakeResponse(chunks=[b"bad data"])
    session = FakeSession(response=response)

    with pytest.raises(SystemExit, match="content checksum verification failed"):
        uploader.verify_drive_file_bytes(
            session,
            {},
            "private-file-id",
            len(b"expected"),
            hashlib.md5(b"expected", usedforsecurity=False).hexdigest(),
        )

    assert response.closed is True


def test_drive_read_back_rejects_oversized_download():
    response = FakeResponse(chunks=[b"too many bytes"])
    session = FakeSession(response=response)

    with pytest.raises(SystemExit, match="exceeds the local archive"):
        uploader.verify_drive_file_bytes(
            session,
            {},
            "private-file-id",
            4,
            hashlib.md5(b"1234", usedforsecurity=False).hexdigest(),
        )

    assert response.closed is True


def test_drive_read_back_rejects_http_errors():
    response = FakeResponse(status_code=404)
    session = FakeSession(response=response)

    with pytest.raises(SystemExit, match="HTTP 404"):
        uploader.verify_drive_file_bytes(
            session,
            {},
            "private-file-id",
            0,
            hashlib.md5(b"", usedforsecurity=False).hexdigest(),
        )

    assert response.closed is True


def test_drive_read_back_reports_network_errors_without_exposing_ids():
    session = FakeSession(error=requests.ConnectionError("private file identifier"))

    with pytest.raises(SystemExit, match="could not reach the stored object") as error:
        uploader.verify_drive_file_bytes(
            session,
            {},
            "private-file-id",
            10,
            "0" * 32,
        )

    assert "private file identifier" not in str(error.value)
    assert "private-file-id" not in str(error.value)
