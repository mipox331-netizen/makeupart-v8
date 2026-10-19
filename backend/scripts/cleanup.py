import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, or_, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.beauty_job import BeautyJob
from app.models.login_attempt import LoginAttempt
from app.models.refresh_session import RefreshSession
from app.services import google_drive_media
from app.services.google_drive_media import GoogleDriveMediaError

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("makeupart.cleanup")


def cleanup_media() -> int:
    root = settings.media_root_path / "salons"
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.MEDIA_RETENTION_DAYS)
    removed = 0

    # The local media root can be absent after a Render restart. Keep scanning
    # the DB index below so old Drive-only objects still honor retention.
    if root.exists():
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if modified < cutoff:
                    # Delete the private Drive copy before removing the local file.
                    # If cloud deletion fails, retain the local copy so cleanup can retry.
                    google_drive_media.delete_media_file(path)
                    path.unlink()
                    removed += 1
            except GoogleDriveMediaError:
                logger.exception("Failed to remove expired media from private Drive storage: %s", path)
            except OSError:
                logger.exception("Failed to remove media file %s", path)

    # Render's local filesystem is ephemeral. A media file may therefore
    # be absent locally while its private Drive copy still exists. Use retained
    # job records as the authoritative index for expiring those remote objects.
    with SessionLocal() as db:
        expired_jobs = db.execute(
            select(BeautyJob).where(BeautyJob.created_at < cutoff)
        ).scalars().all()

        for job in expired_jobs:
            salon_root = (
                settings.media_root_path / "salons" / str(job.salon_id)
            ).resolve()
            for stored_path in (job.input_file_path, job.output_file_path):
                if not stored_path:
                    continue
                candidate = Path(stored_path).expanduser().resolve()
                try:
                    candidate.relative_to(salon_root)
                except ValueError:
                    logger.error(
                        "Refusing retention cleanup for a media path outside its salon."
                    )
                    continue
                if candidate.exists() and not candidate.is_file():
                    logger.error("Refusing retention cleanup for a non-file media path.")
                    continue
                try:
                    google_drive_media.delete_media_file(candidate)
                except GoogleDriveMediaError:
                    logger.exception(
                        "Failed to expire remote salon media; its job record is retained."
                    )
                    continue
                if candidate.is_file():
                    try:
                        candidate.unlink()
                        removed += 1
                    except OSError:
                        logger.exception("Failed to remove expired local media.")

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


def cleanup_login_attempts() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    with SessionLocal() as db:
        result = db.execute(delete(LoginAttempt).where(LoginAttempt.window_started_at < cutoff))
        db.commit()
        return int(result.rowcount or 0)


def main() -> None:
    media_removed = cleanup_media()
    sessions_removed = cleanup_refresh_sessions()
    attempts_removed = cleanup_login_attempts()
    logger.info(
        "Cleanup complete: media_removed=%s refresh_sessions_removed=%s login_attempts_removed=%s",
        media_removed,
        sessions_removed,
        attempts_removed,
    )


if __name__ == "__main__":
    main()
