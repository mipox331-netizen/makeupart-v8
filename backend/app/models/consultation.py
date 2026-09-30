import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Consultation(TimestampMixin, Base):
    __tablename__ = "consultations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    beauty_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("beauty_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    selected_makeup: Mapped[str] = mapped_column(String(500), nullable=False)
    shade: Mapped[str] = mapped_column(String(100), nullable=False)
    intensity: Mapped[float] = mapped_column(default=0.7, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    before_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    after_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    consent_granted: Mapped[bool] = mapped_column(default=False, nullable=False)

    salon: Mapped["Salon"] = relationship("Salon", back_populates="consultations")
    customer: Mapped["Customer"] = relationship("Customer")
