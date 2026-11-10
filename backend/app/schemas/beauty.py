import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MakeupStyle = Literal[
    "natural", "soft_glam", "bridal_rose", "evening_glam",
    "smokey_eye", "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush", "skin_only",
]
BeautyEngine = Literal["classic", "generative"]
PhotoFinish = Literal["Natural Finish", "Warm Glow", "Soft Glam", "Studio Polish", "Golden Hour"]
GenerativeLook = Literal[
    "natural", "soft_glam", "full_glam", "bridal_glam", "smokey_eye",
    "cat_eye", "eyeshadow", "eyeliner", "lipstick", "blush", "foundation",
    "editorial", "sleek_hair", "soft_curls", "braided_style", "elegant_updo",
]
FaceEdit = Literal[
    "none",
    "hair_black", "hair_brown", "hair_auburn", "hair_blonde",
    "soft_smile", "stubble", "short_beard", "full_beard", "mustache",
    "glasses_round", "glasses_square", "glasses_aviator",
    "slim_face", "v_shape", "age_mature", "youthful_finish",
    "masculine_presentation", "feminine_presentation",
]


class BeautyProcessRequest(BaseModel):
    image_path: str = Field(..., min_length=1)
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    consent_confirmed: bool = False
    makeup_style: MakeupStyle = "natural"
    face_edit: FaceEdit = "none"
    photo_finish: PhotoFinish = "Natural Finish"
    engine: BeautyEngine = "classic"
    generative_look: GenerativeLook = "full_glam"
    external_ai_consent: bool = False
    brightness: float = Field(default=0.0, ge=-0.25, le=0.25)
    contrast: float = Field(default=1.0, ge=0.5, le=1.5)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)
    warmth: float = Field(default=0.0, ge=-0.25, le=0.25)
    sharpness: float = Field(default=0.0, ge=0.0, le=1.0)


class BeautyProcessResponse(BaseModel):
    identity_similarity: float | None = None
    skin_tone: str
    undertone: str
    foundation_match: str
    intensity: float
    processed: bool
    makeup_style: MakeupStyle = "natural"
    face_edit: FaceEdit = "none"
    photo_finish: PhotoFinish = "Natural Finish"
    engine: BeautyEngine = "classic"
    generative_look: GenerativeLook | None = None
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    warmth: float = 0.0
    sharpness: float = 0.0


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
