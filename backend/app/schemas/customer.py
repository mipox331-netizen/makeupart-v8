import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    consent_required: bool = True


class CustomerCreate(CustomerBase):
    @field_validator("consent_required")
    @classmethod
    def consent_cannot_be_disabled(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Customer consent requirements cannot be disabled.")
        return value


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    consent_required: bool | None = None

    @field_validator("consent_required")
    @classmethod
    def consent_cannot_be_disabled(cls, value: bool | None) -> bool | None:
        if value is False:
            raise ValueError("Customer consent requirements cannot be disabled.")
        return value


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salon_id: uuid.UUID
