"""
Database seeder — creates default roles and categories on first run.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import generate_uuid
from app.models.role import Role
from app.models.category import Category, DEFAULT_CATEGORIES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_roles(db: Session) -> None:
    """Create default roles if they don't exist."""
    default_roles = [
        {"name": "user", "description": "Standard user with full personal wallet access"},
        {"name": "admin", "description": "Administrator with user management and audit access"},
        {"name": "super_admin", "description": "Super administrator with full system access"},
    ]

    for role_data in default_roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            db.add(Role(
                name=role_data["name"],
                description=role_data["description"],
                created_at=_now_iso(),
            ))

    db.commit()


def seed_categories(db: Session) -> None:
    """Create default expense/income categories if they don't exist."""
    for cat_data in DEFAULT_CATEGORIES:
        existing = db.query(Category).filter(
            Category.name == cat_data["name"],
            Category.user_id == None,
        ).first()
        if not existing:
            db.add(Category(
                id=generate_uuid(),
                user_id=None,  # System default
                name=cat_data["name"],
                type=cat_data["type"],
                icon=cat_data.get("icon"),
                color=cat_data.get("color"),
                is_active=1,
                created_at=_now_iso(),
            ))

    db.commit()


def seed_all(db: Session) -> None:
    """Run all seeders."""
    seed_roles(db)
    seed_categories(db)
