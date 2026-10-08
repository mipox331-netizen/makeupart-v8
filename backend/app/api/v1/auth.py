import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, is_platform_admin
from app.core.config import settings
from app.core.security import TOKEN_TYPE_REFRESH, create_access_token, create_refresh_token, decode_token
from app.crud.salon import create_salon
from app.crud.user import authenticate_user, create_owner_user, get_user, get_user_by_email
from app.db.session import get_db
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.auth import RefreshRequest, RegisterRequest, RegisterResponse, Token
from app.schemas.salon import SalonCreate, SalonOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_tokens(user: User, db: Session) -> Token:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=_hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.flush()
    return Token(access_token=access_token, refresh_token=refresh_token)


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
    return RegisterResponse(salon=SalonOut.model_validate(salon), user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    tokens = _issue_tokens(user, db)
    db.commit()
    return tokens


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_in: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    payload = decode_token(refresh_in.refresh_token)
    if payload is None or payload.get("type") != TOKEN_TYPE_REFRESH:
        raise invalid
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise invalid

    session = db.execute(
        select(RefreshSession)
        .with_for_update()
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.token_hash == _hash_refresh_token(refresh_in.refresh_token),
            RefreshSession.revoked_at.is_(None),
        )
    ).scalars().first()
    if session is None:
        raise invalid
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise invalid

    user = get_user(db, user_id)
    if user is None or not user.is_active:
        raise invalid

    session.revoked_at = datetime.now(timezone.utc)
    tokens = _issue_tokens(user, db)
    db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(refresh_in: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    payload = decode_token(refresh_in.refresh_token)
    if payload is not None and payload.get("type") == TOKEN_TYPE_REFRESH:
        session = db.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == _hash_refresh_token(refresh_in.refresh_token)
            )
        ).scalars().first()
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserOut:
    payload = UserOut.model_validate(current_user)
    return payload.model_copy(update={"is_platform_admin": is_platform_admin(current_user)})
