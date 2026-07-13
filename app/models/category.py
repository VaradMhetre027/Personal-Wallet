"""
Category model — system defaults + user-created custom categories.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense', 'both')",
            name="ck_category_type",
        ),
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
        Index("ix_cat_user_id", "user_id"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL = system default
    name = Column(String(100), nullable=False)
    type = Column(String(10), nullable=False, default="expense")  # income, expense, both
    icon = Column(String(50), nullable=True)    # Icon identifier for frontend
    color = Column(String(7), nullable=True)    # Hex color code (e.g., #FF5733)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<Category {self.name} ({self.type})>"


# Default categories to seed on first run
DEFAULT_CATEGORIES = [
    # Expense categories
    {"name": "Food & Dining", "type": "expense", "icon": "utensils", "color": "#FF6B6B"},
    {"name": "Transportation", "type": "expense", "icon": "car", "color": "#4ECDC4"},
    {"name": "Shopping", "type": "expense", "icon": "shopping-bag", "color": "#45B7D1"},
    {"name": "Healthcare", "type": "expense", "icon": "heart-pulse", "color": "#96CEB4"},
    {"name": "Education", "type": "expense", "icon": "graduation-cap", "color": "#FFEAA7"},
    {"name": "Entertainment", "type": "expense", "icon": "gamepad", "color": "#DDA0DD"},
    {"name": "Utilities", "type": "expense", "icon": "bolt", "color": "#F0E68C"},
    {"name": "Insurance", "type": "expense", "icon": "shield", "color": "#87CEEB"},
    {"name": "Travel", "type": "expense", "icon": "plane", "color": "#FFA07A"},
    {"name": "Investments", "type": "expense", "icon": "chart-line", "color": "#98D8C8"},
    {"name": "Rent", "type": "expense", "icon": "house", "color": "#C9B1FF"},
    {"name": "Subscriptions", "type": "expense", "icon": "credit-card", "color": "#FFB347"},
    {"name": "Personal Care", "type": "expense", "icon": "spa", "color": "#FFB6C1"},
    {"name": "Gifts & Donations", "type": "expense", "icon": "gift", "color": "#FF69B4"},
    {"name": "Miscellaneous", "type": "expense", "icon": "ellipsis", "color": "#C0C0C0"},
    # Income categories
    {"name": "Salary", "type": "income", "icon": "briefcase", "color": "#2ECC71"},
    {"name": "Freelance", "type": "income", "icon": "laptop", "color": "#3498DB"},
    {"name": "Interest", "type": "income", "icon": "percent", "color": "#E74C3C"},
    {"name": "Dividends", "type": "income", "icon": "trending-up", "color": "#9B59B6"},
    {"name": "Rental Income", "type": "income", "icon": "building", "color": "#1ABC9C"},
    {"name": "Gifts Received", "type": "income", "icon": "gift", "color": "#F39C12"},
    {"name": "Refunds", "type": "income", "icon": "rotate-ccw", "color": "#16A085"},
    {"name": "Other Income", "type": "income", "icon": "plus-circle", "color": "#27AE60"},
    # Transfer (both)
    {"name": "Transfer", "type": "both", "icon": "arrow-right-left", "color": "#7F8C8D"},
]
