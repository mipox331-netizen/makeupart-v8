import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.crud.salon import create_salon
from app.crud.user import authenticate_user, create_owner_user, get_user, get_user_by_email
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RefreshRequest, RegisterRequest, RegisterResponse, Token
from app.schemas.salon import SalonCreate, SalonOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(register_in: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    if get_user_by_email(db, register_in.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    salon = create_salon(
        db,
        SalonCreate(
            name=register_in.salon_name,
            phone=register_in.phone,
            email=register_in.email.lower(),
        ),
    )
    user = create_owner_user(db, register_in, salon.id)
    db.commit()
    db.refresh(salon)
    db.refresh(user)
    return RegisterResponse(
        salon=SalonOut.model_validate(salon), user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_in: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    payload = decode_token(refresh_in.refresh_token)
    if payload is None or payload.get("type") != TOKEN_TYPE_REFRESH:
        raise invalid

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError:
        raise invalid

    user = get_user(db, user_id)
    if user is None or not user.is_active:
        raise invalid
    return _issue_tokens(user)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user
