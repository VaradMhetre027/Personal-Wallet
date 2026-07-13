"""
Wallet Pydantic schemas — request/response validation.
All amounts are in smallest currency unit (paise/cents).
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.enums import WalletType


# ── Request Schemas ──

class WalletCreate(BaseModel):
    """Create a new wallet."""
    name: str = Field(..., min_length=1, max_length=100)
    wallet_type: WalletType = WalletType.CASH
    currency: str = Field("INR", min_length=3, max_length=3)
    description: Optional[str] = None
    is_default: bool = False


class WalletUpdate(BaseModel):
    """Update wallet details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    wallet_type: Optional[WalletType] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class WalletTransfer(BaseModel):
    """Transfer funds between wallets."""
    from_wallet_id: str
    to_wallet_id: str
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit (paise/cents)")
    description: Optional[str] = None


# ── Response Schemas ──

class WalletResponse(BaseModel):
    """Wallet response with formatted balance."""
    id: str
    name: str
    wallet_type: str
    currency: str
    balance: int  # In paise/cents
    balance_formatted: str  # Human-readable (e.g., "₹1,234.56")
    is_frozen: bool
    is_default: bool
    description: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WalletSummaryResponse(BaseModel):
    """Summary of all wallets."""
    total_balance: int
    total_balance_formatted: str
    wallet_count: int
    wallets: List[WalletResponse]
