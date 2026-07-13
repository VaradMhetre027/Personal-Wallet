"""
Auth service — business logic for authentication, registration, and token management.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import json

from sqlalchemy.orm import Session
from fastapi import Request

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    create_password_reset_token,
    generate_totp_secret, get_totp_uri, verify_totp,
    generate_uuid,
)
from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsException, UnauthorizedException, NotFoundException,
    BadRequestException, AccountLockedException, ForbiddenException,
)
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.device import Device, LoginHistory
from app.models.audit import AuditLog


def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_agent(request: Request) -> str:
    """Extract User-Agent from request."""
    return request.headers.get("User-Agent", "unknown")


def _parse_device_type(user_agent: str) -> str:
    """Simple device type detection from User-Agent."""
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    return "desktop"


# ── Registration ──

def register_user(db: Session, email: str, username: str, password: str, full_name: str, phone: Optional[str] = None) -> User:
    """Register a new user with the 'user' role."""
    # Check for existing user
    if db.query(User).filter(User.email == email).first():
        raise AlreadyExistsException("User", "email")
    if db.query(User).filter(User.username == username).first():
        raise AlreadyExistsException("User", "username")

    # Get default 'user' role
    user_role = db.query(Role).filter(Role.name == "user").first()
    if not user_role:
        raise BadRequestException("Default 'user' role not found. Run database seeder.")

    now = _now_iso()
    user = User(
        id=generate_uuid(),
        email=email,
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        is_active=1,
        is_verified=1,  # Auto-verified in local dev
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()  # Get user.id before creating role association

    # Assign 'user' role
    db.add(UserRole(user_id=user.id, role_id=user_role.id))

    # Audit log
    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user.id,
        action="user.register",
        entity_type="user",
        entity_id=user.id,
        new_value=json.dumps({"email": email, "username": username}),
        created_at=now,
    ))

    db.commit()
    db.refresh(user)
    return user


# ── Login ──

def authenticate_user(
    db: Session,
    email: str,
    password: str,
    totp_code: Optional[str],
    request: Request,
) -> dict:
    """
    Authenticate a user. Returns token pair on success.
    Handles brute-force protection, 2FA, device tracking, and login history.
    """
    user = db.query(User).filter(User.email == email).first()
    now = _now_iso()
    ip_address = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    # User not found — generic message to prevent user enumeration
    if not user:
        raise UnauthorizedException("Invalid email or password")

    # Check account lockout
    if user.locked_until:
        lock_time = datetime.fromisoformat(user.locked_until)
        if datetime.now(timezone.utc) < lock_time:
            _log_login(db, user.id, ip_address, "locked", "account_locked", user_agent)
            raise AccountLockedException(user.locked_until)
        else:
            # Lockout expired — reset
            user.failed_login_attempts = 0
            user.locked_until = None

    # Check account is active
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    # Verify password
    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1

        # Lock after max attempts
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = (
                datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            ).isoformat()
            _log_login(db, user.id, ip_address, "locked", "max_attempts_exceeded", user_agent)
            db.commit()
            raise AccountLockedException(user.locked_until)

        _log_login(db, user.id, ip_address, "failed", "invalid_password", user_agent)
        db.commit()
        remaining = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
        raise UnauthorizedException(f"Invalid email or password. {remaining} attempts remaining.")

    # Check 2FA
    if user.is_2fa_enabled:
        if not totp_code:
            raise BadRequestException("2FA code required. Provide 'totp_code' field.")
        if not verify_totp(user.totp_secret, totp_code):
            _log_login(db, user.id, ip_address, "failed", "invalid_2fa_code", user_agent)
            db.commit()
            raise UnauthorizedException("Invalid 2FA code")

    # Success — reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = now

    # Get roles for JWT
    roles = [ur.role.name for ur in user.user_roles]

    # Create tokens
    access_token = create_access_token(data={"sub": user.id, "roles": roles})
    refresh_token = create_refresh_token(data={"sub": user.id})

    # Store refresh token hash
    user.refresh_token_hash = hash_password(refresh_token)

    # Track device
    device = _track_device(db, user.id, ip_address, user_agent, now)

    # Log successful login
    _log_login(db, user.id, ip_address, "success", None, user_agent, device_id=device.id)

    # Audit
    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
        created_at=now,
    ))

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ── Refresh Token ──

def refresh_access_token(db: Session, refresh_token: str) -> dict:
    """Validate refresh token and issue new access token."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise UnauthorizedException("User not found")

        # Verify stored refresh token hash
        if not user.refresh_token_hash or not verify_password(refresh_token, user.refresh_token_hash):
            raise UnauthorizedException("Refresh token has been revoked")

        roles = [ur.role.name for ur in user.user_roles]
        new_access_token = create_access_token(data={"sub": user.id, "roles": roles})

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,  # Reuse existing refresh token
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    except Exception:
        raise UnauthorizedException("Invalid or expired refresh token")


# ── Logout ──

def logout_user(db: Session, user: User) -> None:
    """Invalidate refresh token on logout."""
    user.refresh_token_hash = None
    user.updated_at = _now_iso()
    db.commit()


# ── Password Management ──

def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """Change password (requires current password verification)."""
    if not verify_password(current_password, user.hashed_password):
        raise BadRequestException("Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    user.refresh_token_hash = None  # Force re-login on all devices
    user.updated_at = _now_iso()

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user.id,
        action="user.change_password",
        entity_type="user",
        entity_id=user.id,
        created_at=_now_iso(),
    ))
    db.commit()


def initiate_password_reset(db: Session, email: str) -> Optional[str]:
    """
    Generate a password reset token.
    Returns the token (in real app, this would be emailed).
    Always returns success to prevent user enumeration.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None  # Don't reveal whether email exists

    token = create_password_reset_token(user.id)
    return token


def reset_password(db: Session, token: str, new_password: str) -> None:
    """Reset password using a reset token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            raise BadRequestException("Invalid reset token")

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User")

        user.hashed_password = hash_password(new_password)
        user.refresh_token_hash = None
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = _now_iso()

        db.add(AuditLog(
            id=generate_uuid(),
            user_id=user.id,
            action="user.reset_password",
            entity_type="user",
            entity_id=user.id,
            created_at=_now_iso(),
        ))
        db.commit()
    except Exception:
        raise BadRequestException("Invalid or expired reset token")


# ── Profile ──

def update_profile(db: Session, user: User, **kwargs) -> User:
    """Update user profile fields."""
    for field, value in kwargs.items():
        if value is not None:
            # Check uniqueness for username
            if field == "username":
                existing = db.query(User).filter(User.username == value, User.id != user.id).first()
                if existing:
                    raise AlreadyExistsException("User", "username")
            setattr(user, field, value)

    user.updated_at = _now_iso()
    db.commit()
    db.refresh(user)
    return user


# ── 2FA ──

def setup_2fa(db: Session, user: User) -> dict:
    """Generate TOTP secret for 2FA setup."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, user.email)

    # Store secret (not yet enabled — user must verify first)
    user.totp_secret = secret
    user.updated_at = _now_iso()
    db.commit()

    return {"secret": secret, "uri": uri}


def enable_2fa(db: Session, user: User, code: str) -> None:
    """Verify TOTP code and enable 2FA."""
    if not user.totp_secret:
        raise BadRequestException("Call /auth/2fa/enable first to generate a secret.")

    if not verify_totp(user.totp_secret, code):
        raise BadRequestException("Invalid TOTP code. Try again.")

    user.is_2fa_enabled = 1
    user.updated_at = _now_iso()

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user.id,
        action="user.enable_2fa",
        entity_type="user",
        entity_id=user.id,
        created_at=_now_iso(),
    ))
    db.commit()


def disable_2fa(db: Session, user: User, password: str) -> None:
    """Disable 2FA (requires password confirmation)."""
    if not verify_password(password, user.hashed_password):
        raise BadRequestException("Password is incorrect")

    user.is_2fa_enabled = 0
    user.totp_secret = None
    user.updated_at = _now_iso()

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user.id,
        action="user.disable_2fa",
        entity_type="user",
        entity_id=user.id,
        created_at=_now_iso(),
    ))
    db.commit()


# ── Device Tracking ──

def get_user_devices(db: Session, user_id: str) -> list[Device]:
    """Get all devices for a user."""
    return db.query(Device).filter(Device.user_id == user_id).order_by(Device.last_login_at.desc()).all()


def remove_device(db: Session, user_id: str, device_id: str) -> None:
    """Remove a tracked device."""
    device = db.query(Device).filter(Device.id == device_id, Device.user_id == user_id).first()
    if not device:
        raise NotFoundException("Device", device_id)
    db.delete(device)
    db.commit()


# ── Login History ──

def get_login_history(db: Session, user_id: str, limit: int = 20) -> list[LoginHistory]:
    """Get recent login history for a user."""
    return (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == user_id)
        .order_by(LoginHistory.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Helpers ──

def _track_device(db: Session, user_id: str, ip_address: str, user_agent: str, now: str) -> Device:
    """Find or create a device record based on user_agent + ip."""
    device = (
        db.query(Device)
        .filter(Device.user_id == user_id, Device.user_agent == user_agent)
        .first()
    )
    if device:
        device.ip_address = ip_address
        device.last_login_at = now
    else:
        device = Device(
            id=generate_uuid(),
            user_id=user_id,
            device_name=user_agent[:200] if user_agent else "Unknown",
            device_type=_parse_device_type(user_agent),
            ip_address=ip_address,
            user_agent=user_agent,
            is_trusted=0,
            last_login_at=now,
            created_at=now,
        )
        db.add(device)
    db.flush()
    return device


def _log_login(
    db: Session,
    user_id: str,
    ip_address: str,
    status: str,
    failure_reason: Optional[str],
    user_agent: str,
    device_id: Optional[str] = None,
) -> None:
    """Record a login attempt in history."""
    db.add(LoginHistory(
        id=generate_uuid(),
        user_id=user_id,
        device_id=device_id,
        ip_address=ip_address,
        status=status,
        failure_reason=failure_reason,
        created_at=_now_iso(),
    ))


def user_to_response(user: User) -> dict:
    """Convert User model to response-safe dict."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": bool(user.is_active),
        "is_verified": bool(user.is_verified),
        "is_2fa_enabled": bool(user.is_2fa_enabled),
        "roles": [ur.role.name for ur in user.user_roles],
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
