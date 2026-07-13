"""
Category service — business logic for category management.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.security import generate_uuid
from app.core.exceptions import (
    NotFoundException, AlreadyExistsException,
    BadRequestException, ForbiddenException,
)
from app.models.category import Category


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cat_to_response(cat: Category) -> dict:
    return {
        "id": cat.id,
        "name": cat.name,
        "type": cat.type,
        "icon": cat.icon,
        "color": cat.color,
        "is_system": cat.user_id is None,
        "is_active": bool(cat.is_active),
        "created_at": cat.created_at,
    }


def list_categories(db: Session, user_id: str) -> list[dict]:
    """List all categories: system defaults + user's custom categories."""
    categories = (
        db.query(Category)
        .filter(
            or_(Category.user_id == None, Category.user_id == user_id),
            Category.is_active == 1,
        )
        .order_by(Category.user_id.asc(), Category.name.asc())  # System first, then custom
        .all()
    )
    return [_cat_to_response(c) for c in categories]


def create_category(
    db: Session,
    user_id: str,
    name: str,
    cat_type: str,
    icon: Optional[str] = None,
    color: Optional[str] = None,
) -> dict:
    """Create a custom category for the user."""
    # Check for duplicate
    existing = (
        db.query(Category)
        .filter(
            or_(Category.user_id == user_id, Category.user_id == None),
            Category.name == name,
            Category.is_active == 1,
        )
        .first()
    )
    if existing:
        raise AlreadyExistsException("Category", "name")

    category = Category(
        id=generate_uuid(),
        user_id=user_id,
        name=name,
        type=cat_type,
        icon=icon,
        color=color,
        is_active=1,
        created_at=_now_iso(),
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return _cat_to_response(category)


def update_category(db: Session, user_id: str, category_id: str, **kwargs) -> dict:
    """Update a custom category. Cannot edit system defaults."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise NotFoundException("Category", category_id)

    if category.user_id is None:
        raise ForbiddenException("Cannot modify system default categories")

    if category.user_id != user_id:
        raise ForbiddenException("Cannot modify another user's category")

    for field, value in kwargs.items():
        if value is not None:
            setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return _cat_to_response(category)


def delete_category(db: Session, user_id: str, category_id: str) -> None:
    """Deactivate a custom category (soft delete)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise NotFoundException("Category", category_id)

    if category.user_id is None:
        raise ForbiddenException("Cannot delete system default categories")

    if category.user_id != user_id:
        raise ForbiddenException("Cannot delete another user's category")

    category.is_active = 0
    db.commit()
