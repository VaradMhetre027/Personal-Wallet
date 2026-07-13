"""
Security utilities: JWT token management, password hashing, TOTP.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import uuid

from jose import jwt, JWTError
import bcrypt
import hashlib
import base64
import pyotp

from app.core.config import settings


# ── Password Hashing ──

def _prehash(password: str) -> bytes:
    """
    Pre-hash password with SHA-256 and base64-encode.
    This is a standard pattern (used by Dropbox, Django) to handle
    bcrypt's 72-byte input limit while preserving full entropy.
    """
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt (cost factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        _prehash(plain_password),
        hashed_password.encode("utf-8"),
    )


# ── JWT Tokens ──
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    Payload includes: sub (user_id), roles, exp, iat, jti.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),  # Unique token ID
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token with longer expiry.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def create_password_reset_token(user_id: str) -> str:
    """Create a short-lived token for password reset (30 minutes)."""
    return create_access_token(
        data={"sub": user_id, "type": "password_reset"},
        expires_delta=timedelta(minutes=30),
    )


# ── TOTP (2FA) ──
def generate_totp_secret() -> str:
    """Generate a new TOTP secret for 2FA setup."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """Generate the otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against the secret. Allows 1 window of tolerance."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── UUID Generation ──
def generate_uuid() -> str:
    """Generate a new UUID v4 as a string."""
    return str(uuid.uuid4())
