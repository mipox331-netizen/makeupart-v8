import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, or_

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.refresh_session import RefreshSession

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("makeupart.cleanup")


def cleanup_media() -> int:
    root = settings.media_root_path / "salons"
    if not root.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.MEDIA_RETENTION_DAYS)
    removed = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            logger.exception("Failed to remove media file %s", path)

    return removed


def cleanup_refresh_sessions() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.REFRESH_SESSION_RETENTION_DAYS)
    with SessionLocal() as db:
        result = db.execute(
            delete(RefreshSession).where(
                or_(
                    RefreshSession.expires_at < datetime.now(timezone.utc),
                    RefreshSession.revoked_at < cutoff,
                )
            )
        )
        db.commit()
        return int(result.rowcount or 0)


def main() -> None:
    media_removed = cleanup_media()
    sessions_removed = cleanup_refresh_sessions()
    logger.info(
        "Cleanup complete: media_removed=%s refresh_sessions_removed=%s",
        media_removed,
        sessions_removed,
    )


if __name__ == "__main__":
    main()
