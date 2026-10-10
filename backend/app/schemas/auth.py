from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.salon import SalonOut
from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    salon_name: str = Field(min_length=2, max_length=150)
    owner_full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes for bcrypt.")
        return value


class RegisterResponse(BaseModel):
    salon: SalonOut
    user: UserOut


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
