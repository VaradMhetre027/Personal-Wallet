"""
FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User


# ── Bearer Token Extraction ──
security_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Enter the JWT access token",
    auto_error=False,  # We'll handle missing tokens ourselves for better error messages
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: Extract and validate JWT, return the User object.
    Raises 401 if token is missing, invalid, or user doesn't exist.
    """
    if credentials is None:
        raise UnauthorizedException("Authentication required. Provide a Bearer token.")

    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type. Use an access token.")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Token payload missing 'sub' claim.")
    except JWTError:
        raise UnauthorizedException("Token is invalid or has expired.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise UnauthorizedException("User not found or account is deactivated.")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: Ensure the user is active (not suspended).
    """
    if not current_user.is_active:
        raise ForbiddenException("Your account has been suspended.")
    return current_user


class RoleChecker:
    """
    Dependency class for role-based access control.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(RoleChecker(["admin", "super_admin"]))])
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_roles = [ur.role.name for ur in current_user.user_roles]
        if not any(role in self.allowed_roles for role in user_roles):
            raise ForbiddenException(
                f"This action requires one of the following roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


# ── Convenience: pre-built role checkers ──
require_admin = RoleChecker(["admin", "super_admin"])
require_super_admin = RoleChecker(["super_admin"])
