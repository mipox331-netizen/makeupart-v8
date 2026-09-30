import uuid

from sqlalchemy import Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class BeautyResult(TimestampMixin, Base):
    __tablename__ = "beauty_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    beauty_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("beauty_jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    before_image_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    after_image_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    identity_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skin_tone: Mapped[str] = mapped_column(String(50), nullable=False)
    undertone: Mapped[str] = mapped_column(String(50), nullable=False)
    foundation_match: Mapped[str] = mapped_column(String(100), nullable=False)
    watermark_applied: Mapped[bool] = mapped_column(default=False, nullable=False)

    salon: Mapped["Salon"] = relationship("Salon", back_populates="beauty_results")
    beauty_job: Mapped["BeautyJob"] = relationship("BeautyJob", back_populates="result")
