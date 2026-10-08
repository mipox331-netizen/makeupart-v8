import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, is_platform_admin, require_platform_admin, require_roles
from app.crud.user import (
    create_staff_user,
    delete_user,
    get_user,
    get_user_by_email,
    list_salon_users,
    update_user,
)
from app.db.session import get_db
from app.models.salon import Salon
from app.models.subscription import Subscription
from app.models.user import User, UserRole
from app.schemas.user import AdminUserOut, AdminUserStatusUpdate, UserCreateStaff, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin/users", tags=["admin-users"])


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


def _admin_user_query():
    return (
        select(User, Salon, Subscription)
        .join(Salon, User.salon_id == Salon.id)
        .outerjoin(Subscription, Subscription.salon_id == Salon.id)
        .order_by(User.created_at.desc())
    )


def _to_admin_user(
    user: User,
    salon: Salon,
    subscription: Subscription | None,
) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        salon_id=salon.id,
        salon_name=salon.name,
        plan=subscription.plan if subscription is not None else salon.subscription_plan.value,
        subscription_status=subscription.status if subscription is not None else "missing",
        current_period_end=subscription.current_period_end if subscription is not None else None,
        is_platform_admin=is_platform_admin(user),
    )


@admin_router.get("", response_model=list[AdminUserOut])
def list_platform_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_platform_admin),
) -> list[AdminUserOut]:
    rows = db.execute(_admin_user_query()).all()
    return [_to_admin_user(user, salon, subscription) for user, salon, subscription in rows]


@admin_router.patch("/{user_id}/status", response_model=AdminUserOut)
def set_platform_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_platform_admin),
) -> AdminUserOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own admin account",
        )
    if is_platform_admin(target) and target.id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin accounts cannot be disabled",
        )

    target.is_active = payload.is_active
    db.add(target)
    db.commit()

    row = db.execute(_admin_user_query().where(User.id == target.id)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_admin_user(*row)
