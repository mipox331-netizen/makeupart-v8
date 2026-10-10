import uuid
from typing import Literal

from pydantic import BaseModel, Field


WatermarkPosition = Literal["bottom-right", "bottom-left", "top-right", "top-left"]


class WatermarkOut(BaseModel):
    id: uuid.UUID
    salon_id: uuid.UUID
    logo_url: str | None = None
    salon_name: bool
    phone: bool
    instagram: bool
    tiktok: bool
    position: WatermarkPosition
    opacity: float
    size: int

    model_config = {"from_attributes": True}


class WatermarkUpdate(BaseModel):
    logo_url: str | None = Field(default=None, max_length=1000)
    # Salon branding is required for every generated result.
    salon_name: Literal[True] = True
    phone: bool = False
    instagram: bool = False
    tiktok: bool = False
    position: WatermarkPosition = "bottom-right"
    opacity: float = Field(default=0.5, ge=0.0, le=1.0)
    size: int = Field(default=12, ge=8, le=72)
