import io
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.watermark import get_or_create_watermark
from app.schemas.watermark import WatermarkOut, WatermarkUpdate

router = APIRouter(prefix="/watermarks", tags=["watermarks"])

_MAX_LOGO_BYTES = 5 * 1024 * 1024
_MAX_LOGO_PIXELS = 25_000_000
_ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _logo_path(salon_id: uuid.UUID) -> Path:
    return settings.media_root_path / "salons" / str(salon_id) / "branding" / "logo.png"


@router.get("/me", response_model=WatermarkOut)
def read_watermark(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatermarkOut:
    watermark = get_or_create_watermark(db, current_user.salon)
    db.commit()
    db.refresh(watermark)
    return watermark


@router.patch("/me", response_model=WatermarkOut)
def update_watermark(
    watermark_in: WatermarkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    watermark = get_or_create_watermark(db, current_user.salon)
    for field, value in watermark_in.model_dump(exclude_unset=True).items():
        # Logo uploads must use the dedicated, validated binary upload route.
        if field != "logo_url":
            setattr(watermark, field, value)
    db.commit()
    db.refresh(watermark)
    return watermark


@router.post("/me/logo", response_model=WatermarkOut)
async def upload_watermark_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    if (file.content_type or "").lower() not in _ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Logo must be a PNG, JPEG, or WebP image.",
        )

    content = await file.read(_MAX_LOGO_BYTES + 1)
    if not content or len(content) > _MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo must be smaller than 5 MB.",
        )

    try:
        with Image.open(io.BytesIO(content)) as probe:
            width, height = probe.size
            if width <= 0 or height <= 0 or width * height > _MAX_LOGO_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Logo dimensions are too large.",
                )
            probe.verify()
        with Image.open(io.BytesIO(content)) as source:
            logo = ImageOps.exif_transpose(source).convert("RGBA")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded logo is not a valid image.",
        ) from exc

    target = _logo_path(current_user.salon_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".logo-{uuid.uuid4().hex}.tmp")
    try:
        logo.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save salon logo.",
        ) from exc

    watermark = get_or_create_watermark(db, current_user.salon)
    watermark.logo_url = "/api/v1/watermarks/me/logo"
    current_user.salon.logo_url = watermark.logo_url
    db.commit()
    db.refresh(watermark)
    return watermark


@router.get("/me/logo")
def read_watermark_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    watermark = get_or_create_watermark(db, current_user.salon)
    path = _logo_path(current_user.salon_id)
    if not watermark.logo_url or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon logo not found")
    return FileResponse(path, media_type="image/png", filename="salon-logo.png")


@router.delete("/me/logo", response_model=WatermarkOut)
def delete_watermark_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> WatermarkOut:
    watermark = get_or_create_watermark(db, current_user.salon)
    watermark.logo_url = None
    current_user.salon.logo_url = None
    _logo_path(current_user.salon_id).unlink(missing_ok=True)
    db.commit()
    db.refresh(watermark)
    return watermark
