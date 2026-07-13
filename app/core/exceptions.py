"""
Custom exception classes and FastAPI exception handlers.
"""

from fastapi import HTTPException, status


class WalletException(HTTPException):
    """Base exception for the wallet application."""
    pass


class NotFoundException(WalletException):
    """Resource not found."""
    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with ID '{resource_id}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AlreadyExistsException(WalletException):
    """Resource already exists (duplicate)."""
    def __init__(self, resource: str = "Resource", field: str = ""):
        detail = f"{resource} already exists"
        if field:
            detail = f"{resource} with this {field} already exists"
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ForbiddenException(WalletException):
    """User doesn't have permission."""
    def __init__(self, detail: str = "You don't have permission to perform this action"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestException(WalletException):
    """Invalid request."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(WalletException):
    """Authentication failed."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AccountLockedException(WalletException):
    """Account is locked due to too many failed login attempts."""
    def __init__(self, locked_until: str = ""):
        detail = "Account is locked due to too many failed login attempts"
        if locked_until:
            detail += f". Try again after {locked_until}"
        super().__init__(status_code=status.HTTP_423_LOCKED, detail=detail)


class WalletFrozenException(WalletException):
    """Wallet is frozen and cannot process transactions."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This wallet is frozen. Unfreeze it before performing transactions.",
        )


class InsufficientFundsException(WalletException):
    """Not enough balance in wallet."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds in wallet",
        )
