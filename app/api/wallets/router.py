"""
Wallet router — all wallet management endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.api.wallets import schemas, service

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.get("", response_model=schemas.WalletSummaryResponse)
def list_wallets(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all wallets for the current user with total balance."""
    return service.get_wallets(db, current_user.id)


@router.post("", status_code=201)
def create_wallet(
    payload: schemas.WalletCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new wallet."""
    return service.create_wallet(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        wallet_type=payload.wallet_type.value,
        currency=payload.currency,
        description=payload.description,
        is_default=payload.is_default,
    )


@router.get("/{wallet_id}", response_model=schemas.WalletResponse)
def get_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get wallet details with balance."""
    return service.get_wallet(db, current_user.id, wallet_id)


@router.put("/{wallet_id}", response_model=schemas.WalletResponse)
def update_wallet(
    wallet_id: str,
    payload: schemas.WalletUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update wallet name, type, or description."""
    update_data = payload.model_dump(exclude_unset=True)
    # Convert enum to string value if present
    if "wallet_type" in update_data and update_data["wallet_type"] is not None:
        update_data["wallet_type"] = update_data["wallet_type"].value
    return service.update_wallet(db, current_user.id, wallet_id, **update_data)


@router.delete("/{wallet_id}", status_code=204)
def delete_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a wallet (must have zero balance)."""
    service.delete_wallet(db, current_user.id, wallet_id)


@router.post("/{wallet_id}/freeze", response_model=schemas.WalletResponse)
def freeze_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Freeze wallet — block all transactions."""
    return service.freeze_wallet(db, current_user.id, wallet_id)


@router.post("/{wallet_id}/unfreeze", response_model=schemas.WalletResponse)
def unfreeze_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Unfreeze wallet — allow transactions again."""
    return service.unfreeze_wallet(db, current_user.id, wallet_id)


@router.post("/transfer")
def transfer(
    payload: schemas.WalletTransfer,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Transfer funds between own wallets."""
    return service.transfer_between_wallets(
        db=db,
        user_id=current_user.id,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
        description=payload.description,
    )


@router.get("/{wallet_id}/statement")
def wallet_statement(
    wallet_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get wallet transaction history (paginated)."""
    return service.get_wallet_statement(db, current_user.id, wallet_id, page, per_page)
