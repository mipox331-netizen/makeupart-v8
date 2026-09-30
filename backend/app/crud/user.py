import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserCreateStaff, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return db.execute(stmt).scalar_one_or_none()


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def list_salon_users(db: Session, salon_id: uuid.UUID) -> list[User]:
    stmt = select(User).where(User.salon_id == salon_id).order_by(User.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def create_owner_user(db: Session, register_in: RegisterRequest, salon_id: uuid.UUID) -> User:
    user = User(
        email=register_in.email.lower(),
        hashed_password=get_password_hash(register_in.password),
        full_name=register_in.owner_full_name,
        phone=register_in.phone,
        role=UserRole.OWNER,
        is_active=True,
        is_verified=False,
        salon_id=salon_id,
    )
    db.add(user)
    db.flush()
    return user


def create_staff_user(db: Session, user_in: UserCreateStaff, salon_id: uuid.UUID) -> User:
    user = User(
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone=user_in.phone,
        role=UserRole.STAFF,
        is_active=True,
        is_verified=False,
        salon_id=salon_id,
    )
    db.add(user)
    db.flush()
    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    db.flush()
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.flush()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
