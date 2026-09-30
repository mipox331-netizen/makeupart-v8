import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class BeautyJobStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BeautyJob(TimestampMixin, Base):
    __tablename__ = "beauty_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[BeautyJobStatus] = mapped_column(
        Enum(BeautyJobStatus, name="beauty_job_status"), default=BeautyJobStatus.QUEUED, nullable=False
    )
    selected_makeup: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    intensity: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    shade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    before_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    after_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    input_file_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    output_file_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    salon: Mapped["Salon"] = relationship("Salon", back_populates="beauty_jobs")
    customer: Mapped["Customer"] = relationship("Customer")
    result: Mapped["BeautyResult"] = relationship("BeautyResult", back_populates="beauty_job", uselist=False)
