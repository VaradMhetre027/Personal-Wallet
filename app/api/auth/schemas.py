"""
Auth Pydantic schemas — request/response validation.
Never exposes hashed_password, totp_secret, or refresh_token_hash.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
import re


# ── Request Schemas ──

class UserRegister(BaseModel):
    """Registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Enforce strong password policy."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    """Login request."""
    email: EmailStr
    password: str
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class PasswordChange(BaseModel):
    """Change password (requires current password)."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class ForgotPasswordRequest(BaseModel):
    """Request password reset."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    """Update user profile."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    username: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")


class TOTPVerify(BaseModel):
    """Verify a TOTP code."""
    code: str = Field(..., min_length=6, max_length=6)


class RefreshTokenRequest(BaseModel):
    """Refresh access token."""
    refresh_token: str


# ── Response Schemas ──

class TokenResponse(BaseModel):
    """JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User profile response — never includes sensitive fields."""
    id: str
    email: str
    username: str
    full_name: str
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    roles: List[str] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TOTPSetupResponse(BaseModel):
    """2FA setup response with secret and QR URI."""
    secret: str
    uri: str
    message: str = "Scan the QR code with your authenticator app, then verify with a code."


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class DeviceResponse(BaseModel):
    """Device info response."""
    id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    is_trusted: bool
    last_login_at: str
    created_at: str

    model_config = {"from_attributes": True}


class LoginHistoryResponse(BaseModel):
    """Login history entry response."""
    id: str
    ip_address: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    created_at: str
    device: Optional[DeviceResponse] = None

    model_config = {"from_attributes": True}
