import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BeautyProcessRequest(BaseModel):
    image_path: str = Field(..., min_length=1)
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    skin_tone: str | None = None
    undertone: str | None = None
    foundation_match: str | None = None
    melanin_index: float = Field(default=2.0, ge=0.0, le=10.0)
    consent_confirmed: bool = False


class BeautyProcessResponse(BaseModel):
    identity_similarity: float
    skin_tone: str
    undertone: str
    foundation_match: str
    intensity: float
    processed: bool


class BeautyUploadResponse(BeautyProcessResponse):
    job_id: uuid.UUID
    before_image_url: str
    after_image_url: str


class BeautyJobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    salon_id: uuid.UUID
    customer_id: uuid.UUID | None
    status: str
    selected_makeup: str
    intensity: float
    shade: str | None
    notes: str | None
    before_image_url: str | None
    after_image_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class BeautyJobImageKind(BaseModel):
    kind: str = Field(pattern=r"^(before|after)$")
