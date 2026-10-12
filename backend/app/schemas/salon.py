import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.salon import SubscriptionPlan


class SalonBase(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    instagram: str | None = None
    tiktok: str | None = None
    facebook: str | None = None
    location: str | None = None
    logo_url: str | None = None


class SalonCreate(SalonBase):
    pass


class SalonUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    instagram: str | None = None
    tiktok: str | None = None
    facebook: str | None = None
    location: str | None = None
    logo_url: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def name_cannot_be_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Salon name cannot be null.")
        return value


class SalonOut(SalonBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subscription_plan: SubscriptionPlan
