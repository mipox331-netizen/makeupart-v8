import uuid
from enum import Enum as PyEnum

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class SubscriptionPlan(str, PyEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Salon(TimestampMixin, Base):
    __tablename__ = "salons"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tiktok: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facebook: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscription_plan"),
        default=SubscriptionPlan.FREE,
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="salon", cascade="all, delete-orphan"
    )
    customers: Mapped[list["Customer"]] = relationship(
        "Customer", back_populates="salon", cascade="all, delete-orphan"
    )
    beauty_jobs: Mapped[list["BeautyJob"]] = relationship(
        "BeautyJob", back_populates="salon", cascade="all, delete-orphan"
    )
    beauty_results: Mapped[list["BeautyResult"]] = relationship(
        "BeautyResult", back_populates="salon", cascade="all, delete-orphan"
    )
    consultations: Mapped[list["Consultation"]] = relationship(
        "Consultation", back_populates="salon", cascade="all, delete-orphan"
    )
    consents: Mapped[list["ConsentRecord"]] = relationship(
        "ConsentRecord", back_populates="salon", cascade="all, delete-orphan"
    )
    watermark: Mapped["Watermark"] = relationship(
        "Watermark", back_populates="salon", uselist=False, cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="salon", uselist=False, cascade="all, delete-orphan"
    )
