import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("salon_id", name="subscriptions_salon_id_key"),
        Index("ix_subscriptions_salon_id", "salon_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="trialing", nullable=False)
    usage_period_start: Mapped[date] = mapped_column(
        Date, default=lambda: datetime.now(timezone.utc).date().replace(day=1), nullable=False
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    beauty_jobs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    salon: Mapped["Salon"] = relationship("Salon", back_populates="subscription")
