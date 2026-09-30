import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Watermark(TimestampMixin, Base):
    __tablename__ = "watermarks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    logo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    salon_name: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    phone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    instagram: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tiktok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[str] = mapped_column(String(20), default="bottom-right", nullable=False)
    opacity: Mapped[float] = mapped_column(default=0.5, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=12, nullable=False)

    salon: Mapped["Salon"] = relationship("Salon", back_populates="watermark")
