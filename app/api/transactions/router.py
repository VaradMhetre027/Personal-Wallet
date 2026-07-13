"""
Transaction router — all transaction management endpoints.
"""

import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.api.transactions import schemas, service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=schemas.TransactionListResponse)
def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    wallet_id: str | None = None,
    category_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List transactions with filters and pagination."""
    return service.list_transactions(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        wallet_id=wallet_id,
        category_id=category_id,
        txn_type=type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )


@router.post("", status_code=201)
def create_transaction(
    payload: schemas.TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new transaction (income/expense/refund)."""
    return service.create_transaction(
        db=db,
        user_id=current_user.id,
        wallet_id=payload.wallet_id,
        txn_type=payload.type.value,
        amount=payload.amount,
        category_id=payload.category_id,
        description=payload.description,
        transaction_date=payload.transaction_date,
    )


@router.get("/export")
def export_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    format: str = Query("csv", pattern=r"^(csv|excel)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export transactions as CSV or Excel."""
    data = service.export_transactions(db, current_user.id, start_date, end_date, format)

    if format == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        content = output.getvalue()
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
    else:
        # Excel export using openpyxl
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"

        if data:
            ws.append(list(data[0].keys()))
            for row in data:
                ws.append(list(row.values()))

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=transactions.xlsx"},
        )


@router.get("/{txn_id}")
def get_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get single transaction detail."""
    return service.get_transaction(db, current_user.id, txn_id)


@router.put("/{txn_id}")
def update_transaction(
    txn_id: str,
    payload: schemas.TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update transaction details."""
    update_data = payload.model_dump(exclude_unset=True)
    return service.update_transaction(db, current_user.id, txn_id, **update_data)


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Cancel a transaction."""
    service.delete_transaction(db, current_user.id, txn_id)


@router.post("/{txn_id}/reverse")
def reverse_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Reverse a completed transaction (creates a reversal record)."""
    return service.reverse_transaction(db, current_user.id, txn_id)
