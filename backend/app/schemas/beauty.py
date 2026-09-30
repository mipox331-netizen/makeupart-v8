from uuid import UUID

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
    job_id: UUID
    before_image_url: str
    after_image_url: str


class BeautyJobImageKind(BaseModel):
    kind: str = Field(pattern=r"^(before|after)$")
