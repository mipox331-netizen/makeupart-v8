import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsentCreate(BaseModel):
    customer_id: uuid.UUID
    granted: bool
    consent_text: str = Field(min_length=5, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None


class ConsentOut(ConsentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salon_id: uuid.UUID
