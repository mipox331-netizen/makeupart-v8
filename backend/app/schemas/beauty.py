import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MakeupStyle = Literal[
    "natural", "soft_glam", "bridal_rose", "evening_glam",
    "smokey_eye", "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush",
]
BeautyEngine = Literal["classic", "generative"]
GenerativeLook = Literal[
    "natural", "soft_glam", "full_glam", "bridal_glam", "smokey_eye",
    "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush", "foundation",
    "editorial", "sleek_hair", "soft_curls", "braided_style", "elegant_updo",
]


class BeautyProcessRequest(BaseModel):
    image_path: str = Field(..., min_length=1)
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    consent_confirmed: bool = False
    makeup_style: MakeupStyle = "natural"
    engine: BeautyEngine = "classic"
    generative_look: GenerativeLook = "full_glam"
    external_ai_consent: bool = False


class BeautyProcessResponse(BaseModel):
    identity_similarity: float | None = None
    skin_tone: str
    undertone: str
    foundation_match: str
    intensity: float
    processed: bool
    makeup_style: MakeupStyle = "natural"
    engine: BeautyEngine = "classic"
    generative_look: GenerativeLook | None = None


class BeautyUploadResponse(BeautyProcessResponse):
    job_id: uuid.UUID
    before_image_url: str
    after_image_url: str
    watermark_applied: bool


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
