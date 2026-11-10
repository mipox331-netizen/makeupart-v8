import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    token_version: int = 0,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "ver": int(token_version),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, token_version: int = 0) -> str:
    return _create_token(
        subject,
        TOKEN_TYPE_ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_version,
    )


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    return _create_token(
        subject,
        TOKEN_TYPE_REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_version,
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None


_ADMIN_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
_ADMIN_PASSWORD_HASH_ITERATIONS = 600_000


def hash_admin_password(password: str) -> str:
    """Create a server-side PBKDF2 hash for the optional dashboard alias."""
    if not password or len(password.encode("utf-8")) > 1024:
        raise ValueError("Admin password must contain 1 to 1024 UTF-8 bytes.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ADMIN_PASSWORD_HASH_ITERATIONS,
        dklen=32,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return (
        _ADMIN_PASSWORD_HASH_SCHEME
        + "$" + str(_ADMIN_PASSWORD_HASH_ITERATIONS)
        + "$" + salt_text
        + "$" + digest_text
    )


def verify_admin_password(password: str, encoded_hash: str) -> bool:
    """Verify the dashboard alias secret without storing it in app source or APK."""
    try:
        scheme, iteration_text, salt_text, digest_text = encoded_hash.split("$", 3)
        iterations = int(iteration_text)
        if (
            scheme != _ADMIN_PASSWORD_HASH_SCHEME
            or iterations < 300_000
            or iterations > 2_000_000
            or not password
            or len(password.encode("utf-8")) > 1024
        ):
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False
