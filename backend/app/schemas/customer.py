import uuid

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    consent_required: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    consent_required: bool | None = None


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salon_id: uuid.UUID
