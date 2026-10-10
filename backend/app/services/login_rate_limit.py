import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.login_attempt import LoginAttempt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    # SQLite does not preserve timezone metadata in DateTime columns.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def is_login_locked(db: Session, email: str) -> bool:
    attempt = db.execute(
        select(LoginAttempt).where(LoginAttempt.email_hash == _email_hash(email)).with_for_update()
    ).scalars().first()
    if attempt is None or attempt.locked_until is None:
        return False
    return _aware(attempt.locked_until) > _now()


def record_login_failure(db: Session, email: str) -> None:
    key = _email_hash(email)
    now = _now()
    window = timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    lockout = timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)

    # Retry once if simultaneous first failures race to create the unique row.
    for _ in range(2):
        attempt = db.execute(
            select(LoginAttempt).where(LoginAttempt.email_hash == key).with_for_update()
        ).scalars().first()
        if attempt is None:
            db.add(LoginAttempt(email_hash=key, failed_attempts=1, window_started_at=now))
        elif _aware(attempt.window_started_at) + window <= now:
            attempt.failed_attempts = 1
            attempt.window_started_at = now
            attempt.locked_until = None
        else:
            attempt.failed_attempts += 1
            if attempt.failed_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                attempt.locked_until = now + lockout
        try:
            db.commit()
            return
        except IntegrityError:
            db.rollback()
    raise RuntimeError("Could not record failed login attempt")


def clear_login_failures(db: Session, email: str) -> None:
    attempt = db.execute(
        select(LoginAttempt).where(LoginAttempt.email_hash == _email_hash(email)).with_for_update()
    ).scalars().first()
    if attempt is not None:
        db.delete(attempt)
