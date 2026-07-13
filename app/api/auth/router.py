"""
Auth router — all authentication endpoints.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.api.auth import schemas, service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(
    payload: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    """Register a new user account."""
    user = service.register_user(
        db=db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    return service.user_to_response(user)


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate and receive JWT + refresh token."""
    return service.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
        totp_code=payload.totp_code,
        request=request,
    )


@router.post("/logout", response_model=schemas.MessageResponse)
def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Invalidate refresh token."""
    service.logout_user(db, current_user)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Get new access token using refresh token."""
    return service.refresh_access_token(db, payload.refresh_token)


@router.post("/forgot-password", response_model=schemas.MessageResponse)
def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate password reset.
    In local dev, returns the reset token directly.
    In production, this would send an email.
    """
    token = service.initiate_password_reset(db, payload.email)
    if token:
        # DEV ONLY: return token directly. In production, send via email.
        return {
            "message": "Password reset token generated",
            "detail": f"DEV_TOKEN: {token}",
        }
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(
    payload: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password using reset token."""
    service.reset_password(db, payload.token, payload.new_password)
    return {"message": "Password has been reset successfully. Please login with your new password."}


@router.put("/change-password", response_model=schemas.MessageResponse)
def change_password(
    payload: schemas.PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password (requires current password)."""
    service.change_password(db, current_user, payload.current_password, payload.new_password)
    return {"message": "Password changed successfully. All other sessions have been invalidated."}


@router.get("/me", response_model=schemas.UserResponse)
def get_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return service.user_to_response(current_user)


@router.put("/me", response_model=schemas.UserResponse)
def update_profile(
    payload: schemas.UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    updated_fields = payload.model_dump(exclude_unset=True)
    user = service.update_profile(db, current_user, **updated_fields)
    return service.user_to_response(user)


@router.post("/2fa/enable", response_model=schemas.TOTPSetupResponse)
def enable_2fa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate TOTP secret and QR code URI for 2FA setup."""
    result = service.setup_2fa(db, current_user)
    return result


@router.post("/2fa/verify", response_model=schemas.MessageResponse)
def verify_2fa(
    payload: schemas.TOTPVerify,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Verify TOTP code and activate 2FA."""
    service.enable_2fa(db, current_user, payload.code)
    return {"message": "2FA has been enabled successfully."}


@router.post("/2fa/disable", response_model=schemas.MessageResponse)
def disable_2fa(
    payload: schemas.PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Disable 2FA (requires password confirmation)."""
    service.disable_2fa(db, current_user, payload.current_password)
    return {"message": "2FA has been disabled."}


@router.get("/devices", response_model=list[schemas.DeviceResponse])
def list_devices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user's registered devices."""
    devices = service.get_user_devices(db, current_user.id)
    return devices


@router.delete("/devices/{device_id}", response_model=schemas.MessageResponse)
def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a tracked device."""
    service.remove_device(db, current_user.id, device_id)
    return {"message": "Device removed successfully"}


@router.get("/login-history", response_model=list[schemas.LoginHistoryResponse])
def login_history(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recent login history."""
    return service.get_login_history(db, current_user.id, limit)
