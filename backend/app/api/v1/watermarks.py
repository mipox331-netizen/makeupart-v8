from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.watermark import get_or_create_watermark
from app.schemas.watermark import WatermarkOut, WatermarkUpdate

router = APIRouter(prefix="/watermarks", tags=["watermarks"])


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
    for field, value in watermark_in.model_dump().items():
        setattr(watermark, field, value)
    db.commit()
    db.refresh(watermark)
    return watermark
