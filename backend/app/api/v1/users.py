import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.crud.user import (
    create_staff_user,
    delete_user,
    get_user,
    get_user_by_email,
    list_salon_users,
    update_user,
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreateStaff, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_own_profile(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_own_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    user = update_user(db, current_user, user_in)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> list[User]:
    return list_salon_users(db, current_user.salon_id)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    user_in: UserCreateStaff,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> User:
    if get_user_by_email(db, user_in.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    user = create_staff_user(db, user_in, current_user.salon_id)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_staff(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
) -> None:
    target = get_user(db, user_id)
    if target is None or target.salon_id != current_user.salon_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )
    if target.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner accounts cannot be deleted through this endpoint",
        )
    if current_user.role == UserRole.ADMIN and target.role != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can only remove staff accounts",
        )
    delete_user(db, target)
    db.commit()
