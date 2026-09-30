import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsultationCreate(BaseModel):
    customer_id: uuid.UUID
    beauty_job_id: uuid.UUID | None = None
    selected_makeup: str = Field(min_length=1, max_length=500)
    shade: str = Field(min_length=1, max_length=100)
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    notes: str | None = None
    before_image_url: str | None = None
    after_image_url: str | None = None
    consent_granted: bool = False


class ConsultationOut(ConsultationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    salon_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
