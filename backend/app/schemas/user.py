import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = None


class UserCreateStaff(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    salon_id: uuid.UUID
    is_platform_admin: bool = False


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: UserRole
    is_active: bool
    is_verified: bool
    salon_id: uuid.UUID
    salon_name: str
    plan: str
    subscription_status: str
    current_period_end: datetime | None
    is_platform_admin: bool = False


class AdminUserStatusUpdate(BaseModel):
    is_active: bool
