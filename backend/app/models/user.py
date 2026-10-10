import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class UserRole(str, PyEnum):
    OWNER = "owner"
    STAFF = "staff"
    ADMIN = "admin"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.STAFF, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Keep compatibility with existing production databases that enforce this legacy column.
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    salon_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"), nullable=False
    )
    salon: Mapped["Salon"] = relationship("Salon", back_populates="users")
