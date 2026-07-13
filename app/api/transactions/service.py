"""
Transaction service — business logic for recording, querying, and managing transactions.
"""

from datetime import datetime, timezone
from typing import Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.security import generate_uuid
from app.core.exceptions import (
    NotFoundException, BadRequestException,
    WalletFrozenException, InsufficientFundsException,
)
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.models.category import Category
from app.models.audit import AuditLog


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_amount(amount_paise: int, currency: str = "INR") -> str:
    symbols = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    value = amount_paise / 100
    return f"{symbol}{value:,.2f}"


def _txn_to_response(txn: Transaction) -> dict:
    """Convert transaction model to response dict."""
    return {
        "id": txn.id,
        "wallet_id": txn.wallet_id,
        "target_wallet_id": txn.target_wallet_id,
        "type": txn.type,
        "status": txn.status,
        "amount": txn.amount,
        "amount_formatted": _format_amount(txn.amount, txn.currency),
        "currency": txn.currency,
        "description": txn.description,
        "category_name": txn.category.name if txn.category else None,
        "category_icon": txn.category.icon if txn.category else None,
        "category_color": txn.category.color if txn.category else None,
        "is_recurring": bool(txn.is_recurring),
        "transaction_date": txn.transaction_date,
        "created_at": txn.created_at,
    }


# ── Create Transaction ──

def create_transaction(
    db: Session,
    user_id: str,
    wallet_id: str,
    txn_type: str,
    amount: int,
    category_id: Optional[str] = None,
    description: Optional[str] = None,
    transaction_date: Optional[str] = None,
) -> dict:
    """Create a new income or expense transaction."""
    now = _now_iso()

    # Validate wallet
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id, Wallet.user_id == user_id).first()
    if not wallet:
        raise NotFoundException("Wallet", wallet_id)
    if wallet.is_frozen:
        raise WalletFrozenException()

    # Validate category
    if category_id:
        category = db.query(Category).filter(
            Category.id == category_id,
            or_(Category.user_id == user_id, Category.user_id == None),
            Category.is_active == 1,
        ).first()
        if not category:
            raise NotFoundException("Category", category_id)

    # For expense: check balance
    if txn_type == "expense":
        if wallet.balance < amount:
            raise InsufficientFundsException()
        wallet.balance -= amount
    elif txn_type == "income":
        wallet.balance += amount
    elif txn_type == "refund":
        wallet.balance += amount
    else:
        raise BadRequestException(f"Use /wallets/transfer for transfer transactions")

    wallet.updated_at = now

    txn = Transaction(
        id=generate_uuid(),
        user_id=user_id,
        wallet_id=wallet_id,
        category_id=category_id,
        type=txn_type,
        status="completed",
        amount=amount,
        currency=wallet.currency,
        description=description,
        transaction_date=transaction_date or now,
        created_at=now,
        updated_at=now,
    )
    db.add(txn)

    # Audit
    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action=f"transaction.create.{txn_type}",
        entity_type="transaction",
        entity_id=txn.id,
        new_value=json.dumps({
            "wallet_id": wallet_id,
            "amount": amount,
            "type": txn_type,
            "category_id": category_id,
        }),
        created_at=now,
    ))

    db.commit()
    db.refresh(txn)
    return _txn_to_response(txn)


# ── List Transactions ──

def list_transactions(
    db: Session,
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    wallet_id: Optional[str] = None,
    category_id: Optional[str] = None,
    txn_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    search: Optional[str] = None,
) -> dict:
    """List transactions with filters, pagination, and summary totals."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)

    # Apply filters
    if wallet_id:
        query = query.filter(Transaction.wallet_id == wallet_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if txn_type:
        query = query.filter(Transaction.type == txn_type)
    if status:
        query = query.filter(Transaction.status == status)
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date + "T23:59:59")
    if min_amount:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount:
        query = query.filter(Transaction.amount <= max_amount)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))

    # Get totals for the filtered set
    total = query.count()

    income_total = (
        query.filter(Transaction.type == "income", Transaction.status == "completed")
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .scalar()
    )
    expense_total = (
        query.filter(Transaction.type == "expense", Transaction.status == "completed")
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .scalar()
    )

    # Paginate
    transactions = (
        query
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    net = income_total - expense_total

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "total_income": income_total,
        "total_expense": expense_total,
        "net": net,
        "net_formatted": _format_amount(net),
        "transactions": [_txn_to_response(t) for t in transactions],
    }


# ── Get Transaction ──

def get_transaction(db: Session, user_id: str, txn_id: str) -> dict:
    """Get a single transaction by ID."""
    txn = db.query(Transaction).filter(
        Transaction.id == txn_id,
        Transaction.user_id == user_id,
    ).first()
    if not txn:
        raise NotFoundException("Transaction", txn_id)
    return _txn_to_response(txn)


# ── Update Transaction ──

def update_transaction(
    db: Session,
    user_id: str,
    txn_id: str,
    **kwargs,
) -> dict:
    """Update a transaction (limited to description, category, date for completed txns)."""
    txn = db.query(Transaction).filter(
        Transaction.id == txn_id,
        Transaction.user_id == user_id,
    ).first()
    if not txn:
        raise NotFoundException("Transaction", txn_id)

    now = _now_iso()
    old_values = {}

    # For completed transactions, only allow updating non-financial fields
    if txn.status == "completed" and "amount" in kwargs and kwargs["amount"] is not None:
        raise BadRequestException("Cannot change amount of a completed transaction. Reverse it and create a new one.")

    for field, value in kwargs.items():
        if value is not None:
            old_values[field] = getattr(txn, field)
            setattr(txn, field, value)

    txn.updated_at = now

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="transaction.update",
        entity_type="transaction",
        entity_id=txn_id,
        old_value=json.dumps(old_values),
        new_value=json.dumps(kwargs),
        created_at=now,
    ))

    db.commit()
    db.refresh(txn)
    return _txn_to_response(txn)


# ── Delete Transaction ──

def delete_transaction(db: Session, user_id: str, txn_id: str) -> None:
    """Cancel a transaction (soft-delete by setting status to 'cancelled')."""
    txn = db.query(Transaction).filter(
        Transaction.id == txn_id,
        Transaction.user_id == user_id,
    ).first()
    if not txn:
        raise NotFoundException("Transaction", txn_id)

    if txn.status not in ("pending", "completed"):
        raise BadRequestException(f"Cannot cancel a transaction with status '{txn.status}'")

    now = _now_iso()

    # Reverse the balance change
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if wallet and txn.status == "completed":
        if txn.type == "expense":
            wallet.balance += txn.amount
        elif txn.type == "income":
            wallet.balance -= txn.amount
        elif txn.type == "refund":
            wallet.balance -= txn.amount
        wallet.updated_at = now

    txn.status = "cancelled"
    txn.updated_at = now

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="transaction.cancel",
        entity_type="transaction",
        entity_id=txn_id,
        created_at=now,
    ))

    db.commit()


# ── Reverse Transaction ──

def reverse_transaction(db: Session, user_id: str, txn_id: str) -> dict:
    """
    Reverse a completed transaction.
    Creates a new reversal transaction and updates the original status.
    """
    original = db.query(Transaction).filter(
        Transaction.id == txn_id,
        Transaction.user_id == user_id,
    ).first()
    if not original:
        raise NotFoundException("Transaction", txn_id)

    if original.status != "completed":
        raise BadRequestException("Can only reverse completed transactions")

    now = _now_iso()

    # Reverse the wallet balance
    wallet = db.query(Wallet).filter(Wallet.id == original.wallet_id).first()
    if original.type == "expense":
        wallet.balance += original.amount
    elif original.type == "income":
        if wallet.balance < original.amount:
            raise InsufficientFundsException()
        wallet.balance -= original.amount
    elif original.type == "refund":
        if wallet.balance < original.amount:
            raise InsufficientFundsException()
        wallet.balance -= original.amount
    wallet.updated_at = now

    # Mark original as reversed
    original.status = "reversed"
    original.updated_at = now

    # Create reversal transaction
    reversal = Transaction(
        id=generate_uuid(),
        user_id=user_id,
        wallet_id=original.wallet_id,
        category_id=original.category_id,
        type="refund" if original.type == "expense" else "expense",
        status="completed",
        amount=original.amount,
        currency=original.currency,
        description=f"Reversal of transaction {original.id}",
        reference_id=original.id,
        transaction_date=now,
        created_at=now,
        updated_at=now,
    )
    db.add(reversal)

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="transaction.reverse",
        entity_type="transaction",
        entity_id=txn_id,
        new_value=json.dumps({"reversal_id": reversal.id}),
        created_at=now,
    ))

    db.commit()
    db.refresh(reversal)
    return _txn_to_response(reversal)


# ── Export ──

def export_transactions(
    db: Session,
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "csv",
) -> list[dict]:
    """
    Get transactions for export. Returns raw data list.
    The router handles format conversion (CSV/Excel).
    """
    query = db.query(Transaction).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date + "T23:59:59")

    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    return [
        {
            "Date": t.transaction_date,
            "Type": t.type,
            "Status": t.status,
            "Amount": t.amount / 100,  # Convert to currency units for export
            "Currency": t.currency,
            "Category": t.category.name if t.category else "",
            "Description": t.description or "",
            "Wallet": t.wallet.name if t.wallet else "",
        }
        for t in transactions
    ]
