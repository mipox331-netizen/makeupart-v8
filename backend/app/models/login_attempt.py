from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class LoginAttempt(TimestampMixin, Base):
    """Failed-login counters keyed by a one-way hash of the normalized email."""

    __tablename__ = "login_attempts"

    email_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
