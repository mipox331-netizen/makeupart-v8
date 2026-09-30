from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.crud.salon import get_salon, update_salon
from app.db.session import get_db
from app.models.salon import Salon
from app.models.user import User, UserRole
from app.schemas.salon import SalonOut, SalonUpdate

router = APIRouter(prefix="/salons", tags=["salons"])


@router.get("/me", response_model=SalonOut)
def read_own_salon(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
) -> Salon:
    return get_salon(db, current_user.salon_id)


@router.patch("/me", response_model=SalonOut)
def update_own_salon(
    salon_in: SalonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> Salon:
    salon = get_salon(db, current_user.salon_id)
    salon = update_salon(db, salon, salon_in)
    db.commit()
    db.refresh(salon)
    return salon
