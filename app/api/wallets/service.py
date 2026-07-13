"""
Wallet service — business logic for wallet CRUD, transfers, and statements.
"""

from datetime import datetime, timezone
from typing import Optional
import json

from sqlalchemy.orm import Session

from app.core.security import generate_uuid
from app.core.exceptions import (
    NotFoundException, BadRequestException, WalletFrozenException,
    InsufficientFundsException, ForbiddenException,
)
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.audit import AuditLog


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_amount(amount_paise: int, currency: str = "INR") -> str:
    """Format paise/cents to human-readable currency string."""
    symbols = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    value = amount_paise / 100
    return f"{symbol}{value:,.2f}"


def _wallet_to_response(wallet: Wallet) -> dict:
    """Convert wallet model to response dict."""
    return {
        "id": wallet.id,
        "name": wallet.name,
        "wallet_type": wallet.wallet_type,
        "currency": wallet.currency,
        "balance": wallet.balance,
        "balance_formatted": _format_amount(wallet.balance, wallet.currency),
        "is_frozen": bool(wallet.is_frozen),
        "is_default": bool(wallet.is_default),
        "description": wallet.description,
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
    }


# ── CRUD ──

def create_wallet(
    db: Session,
    user_id: str,
    name: str,
    wallet_type: str,
    currency: str = "INR",
    description: Optional[str] = None,
    is_default: bool = False,
) -> dict:
    """Create a new wallet for the user."""
    now = _now_iso()

    # If setting as default, unset other defaults
    if is_default:
        db.query(Wallet).filter(
            Wallet.user_id == user_id, Wallet.is_default == 1
        ).update({"is_default": 0, "updated_at": now})

    wallet = Wallet(
        id=generate_uuid(),
        user_id=user_id,
        name=name,
        wallet_type=wallet_type,
        currency=currency,
        balance=0,
        is_frozen=0,
        is_default=1 if is_default else 0,
        description=description,
        created_at=now,
        updated_at=now,
    )
    db.add(wallet)

    # Audit
    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.create",
        entity_type="wallet",
        entity_id=wallet.id,
        new_value=json.dumps({"name": name, "type": wallet_type, "currency": currency}),
        created_at=now,
    ))

    db.commit()
    db.refresh(wallet)
    return _wallet_to_response(wallet)


def get_wallets(db: Session, user_id: str) -> dict:
    """Get all wallets for a user with summary."""
    wallets = (
        db.query(Wallet)
        .filter(Wallet.user_id == user_id)
        .order_by(Wallet.is_default.desc(), Wallet.created_at.desc())
        .all()
    )

    wallet_responses = [_wallet_to_response(w) for w in wallets]
    total_balance = sum(w.balance for w in wallets)

    return {
        "total_balance": total_balance,
        "total_balance_formatted": _format_amount(total_balance),
        "wallet_count": len(wallets),
        "wallets": wallet_responses,
    }


def get_wallet(db: Session, user_id: str, wallet_id: str) -> dict:
    """Get a single wallet by ID."""
    wallet = _get_user_wallet(db, user_id, wallet_id)
    return _wallet_to_response(wallet)


def update_wallet(
    db: Session,
    user_id: str,
    wallet_id: str,
    **kwargs,
) -> dict:
    """Update wallet details (name, type, description, default status)."""
    wallet = _get_user_wallet(db, user_id, wallet_id)
    now = _now_iso()

    old_values = {}
    for field, value in kwargs.items():
        if value is not None:
            if field == "is_default" and value:
                # Unset other defaults
                db.query(Wallet).filter(
                    Wallet.user_id == user_id,
                    Wallet.is_default == 1,
                    Wallet.id != wallet_id,
                ).update({"is_default": 0, "updated_at": now})
                old_values[field] = bool(wallet.is_default)
                wallet.is_default = 1
            elif field == "is_default" and not value:
                old_values[field] = bool(wallet.is_default)
                wallet.is_default = 0
            else:
                old_values[field] = getattr(wallet, field)
                setattr(wallet, field, value)

    wallet.updated_at = now

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.update",
        entity_type="wallet",
        entity_id=wallet_id,
        old_value=json.dumps(old_values),
        new_value=json.dumps(kwargs),
        created_at=now,
    ))

    db.commit()
    db.refresh(wallet)
    return _wallet_to_response(wallet)


def delete_wallet(db: Session, user_id: str, wallet_id: str) -> None:
    """Soft-delete (or hard delete) a wallet. Must have zero balance."""
    wallet = _get_user_wallet(db, user_id, wallet_id)

    if wallet.balance != 0:
        raise BadRequestException(
            f"Cannot delete wallet with balance {_format_amount(wallet.balance, wallet.currency)}. "
            "Transfer all funds out first."
        )

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.delete",
        entity_type="wallet",
        entity_id=wallet_id,
        old_value=json.dumps({"name": wallet.name, "type": wallet.wallet_type}),
        created_at=_now_iso(),
    ))

    db.delete(wallet)
    db.commit()


# ── Freeze / Unfreeze ──

def freeze_wallet(db: Session, user_id: str, wallet_id: str) -> dict:
    """Freeze a wallet — blocks all transactions."""
    wallet = _get_user_wallet(db, user_id, wallet_id)
    wallet.is_frozen = 1
    wallet.updated_at = _now_iso()

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.freeze",
        entity_type="wallet",
        entity_id=wallet_id,
        created_at=_now_iso(),
    ))

    db.commit()
    db.refresh(wallet)
    return _wallet_to_response(wallet)


def unfreeze_wallet(db: Session, user_id: str, wallet_id: str) -> dict:
    """Unfreeze a wallet — allow transactions again."""
    wallet = _get_user_wallet(db, user_id, wallet_id)
    wallet.is_frozen = 0
    wallet.updated_at = _now_iso()

    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.unfreeze",
        entity_type="wallet",
        entity_id=wallet_id,
        created_at=_now_iso(),
    ))

    db.commit()
    db.refresh(wallet)
    return _wallet_to_response(wallet)


# ── Transfer ──

def transfer_between_wallets(
    db: Session,
    user_id: str,
    from_wallet_id: str,
    to_wallet_id: str,
    amount: int,
    description: Optional[str] = None,
) -> dict:
    """Transfer funds between two wallets owned by the same user."""
    if from_wallet_id == to_wallet_id:
        raise BadRequestException("Cannot transfer to the same wallet")

    from_wallet = _get_user_wallet(db, user_id, from_wallet_id)
    to_wallet = _get_user_wallet(db, user_id, to_wallet_id)

    # Validate
    if from_wallet.is_frozen:
        raise WalletFrozenException()
    if to_wallet.is_frozen:
        raise BadRequestException("Destination wallet is frozen")
    if from_wallet.balance < amount:
        raise InsufficientFundsException()

    now = _now_iso()

    # Update balances
    from_wallet.balance -= amount
    to_wallet.balance += amount
    from_wallet.updated_at = now
    to_wallet.updated_at = now

    # Create transfer transaction record
    txn = Transaction(
        id=generate_uuid(),
        user_id=user_id,
        wallet_id=from_wallet_id,
        target_wallet_id=to_wallet_id,
        type="transfer",
        status="completed",
        amount=amount,
        currency=from_wallet.currency,
        description=description or f"Transfer to {to_wallet.name}",
        transaction_date=now,
        created_at=now,
        updated_at=now,
    )
    db.add(txn)

    # Audit
    db.add(AuditLog(
        id=generate_uuid(),
        user_id=user_id,
        action="wallet.transfer",
        entity_type="wallet",
        entity_id=from_wallet_id,
        new_value=json.dumps({
            "from": from_wallet_id,
            "to": to_wallet_id,
            "amount": amount,
            "transaction_id": txn.id,
        }),
        created_at=now,
    ))

    db.commit()

    return {
        "message": "Transfer successful",
        "amount": amount,
        "amount_formatted": _format_amount(amount, from_wallet.currency),
        "from_wallet": _wallet_to_response(from_wallet),
        "to_wallet": _wallet_to_response(to_wallet),
        "transaction_id": txn.id,
    }


# ── Statement ──

def get_wallet_statement(
    db: Session,
    user_id: str,
    wallet_id: str,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Get paginated transaction history for a specific wallet."""
    _get_user_wallet(db, user_id, wallet_id)  # Verify ownership

    query = (
        db.query(Transaction)
        .filter(
            (Transaction.wallet_id == wallet_id) | (Transaction.target_wallet_id == wallet_id),
            Transaction.user_id == user_id,
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    )

    total = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "wallet_id": wallet_id,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
        "transactions": [
            {
                "id": t.id,
                "type": t.type,
                "status": t.status,
                "amount": t.amount,
                "amount_formatted": _format_amount(t.amount, t.currency),
                "description": t.description,
                "category": t.category.name if t.category else None,
                "transaction_date": t.transaction_date,
            }
            for t in transactions
        ],
    }


# ── Helpers ──

def _get_user_wallet(db: Session, user_id: str, wallet_id: str) -> Wallet:
    """Get a wallet ensuring it belongs to the user."""
    wallet = db.query(Wallet).filter(
        Wallet.id == wallet_id,
        Wallet.user_id == user_id,
    ).first()
    if not wallet:
        raise NotFoundException("Wallet", wallet_id)
    return wallet
