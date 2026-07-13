"""
Transaction Pydantic schemas — request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.enums import TransactionType, TransactionStatus


# ── Request Schemas ──

class TransactionCreate(BaseModel):
    """Create a new transaction (income or expense)."""
    wallet_id: str
    category_id: Optional[str] = None
    type: TransactionType
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit (paise/cents)")
    description: Optional[str] = None
    transaction_date: Optional[str] = None  # ISO 8601; defaults to now


class TransactionUpdate(BaseModel):
    """Update a transaction."""
    category_id: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = Field(None, gt=0)
    transaction_date: Optional[str] = None


class TransactionFilter(BaseModel):
    """Filter parameters for transaction list."""
    wallet_id: Optional[str] = None
    category_id: Optional[str] = None
    type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    search: Optional[str] = None  # Search in description


class RecurringTransactionCreate(BaseModel):
    """Create a recurring transaction rule."""
    wallet_id: str
    category_id: Optional[str] = None
    type: TransactionType
    amount: int = Field(..., gt=0)
    description: Optional[str] = None
    frequency: str = Field(..., pattern=r"^(daily|weekly|monthly|yearly)$")
    start_date: str  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD, null = no end


class RecurringTransactionUpdate(BaseModel):
    """Update a recurring transaction rule."""
    amount: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    frequency: Optional[str] = Field(None, pattern=r"^(daily|weekly|monthly|yearly)$")
    end_date: Optional[str] = None


# ── Response Schemas ──

class TransactionResponse(BaseModel):
    """Single transaction response."""
    id: str
    wallet_id: str
    target_wallet_id: Optional[str] = None
    type: str
    status: str
    amount: int
    amount_formatted: str
    currency: str
    description: Optional[str] = None
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    is_recurring: bool
    transaction_date: str
    created_at: str

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    """Paginated transaction list."""
    page: int
    per_page: int
    total: int
    total_pages: int
    total_income: int
    total_expense: int
    net: int
    net_formatted: str
    transactions: List[TransactionResponse]


class RecurringTransactionResponse(BaseModel):
    """Recurring transaction rule response."""
    id: str
    wallet_id: str
    type: str
    amount: int
    amount_formatted: str
    description: Optional[str] = None
    category_name: Optional[str] = None
    frequency: str
    start_date: str
    end_date: Optional[str] = None
    next_date: Optional[str] = None
    is_active: bool
    created_at: str
