from threading import RLock
from typing import Callable


_lock = RLock()
_commit_callback: Callable[[], object] | None = None


def configure_media_volume(*, commit: Callable[[], object] | None = None) -> None:
    """Inject Modal's mounted-volume commit callback at production app startup."""
    global _commit_callback
    with _lock:
        _commit_callback = commit


def commit_media_volume() -> None:
    """Persist media writes/deletes on Modal; local development remains a no-op."""
    with _lock:
        callback = _commit_callback
        if callback is not None:
            callback()
