"""
Category router — category management endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.api.categories import schemas, service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[schemas.CategoryResponse])
def list_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all categories (system defaults + user custom)."""
    return service.list_categories(db, current_user.id)


@router.post("", response_model=schemas.CategoryResponse, status_code=201)
def create_category(
    payload: schemas.CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a custom category."""
    return service.create_category(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        cat_type=payload.type.value,
        icon=payload.icon,
        color=payload.color,
    )


@router.put("/{category_id}", response_model=schemas.CategoryResponse)
def update_category(
    category_id: str,
    payload: schemas.CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a custom category (cannot edit system defaults)."""
    update_data = payload.model_dump(exclude_unset=True)
    if "type" in update_data and update_data["type"] is not None:
        update_data["type"] = update_data["type"].value
    return service.update_category(db, current_user.id, category_id, **update_data)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Deactivate a custom category."""
    service.delete_category(db, current_user.id, category_id)
