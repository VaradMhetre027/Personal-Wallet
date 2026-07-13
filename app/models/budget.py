"""
Budget and BudgetAlert models — Phase 2 API, schema defined now.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint(
            "period IN ('weekly', 'monthly', 'quarterly', 'yearly')",
            name="ck_budget_period",
        ),
        Index("ix_budget_user_id", "user_id"),
        Index("ix_budget_user_active", "user_id", "is_active"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)  # NULL = overall budget
    name = Column(String(100), nullable=False)
    period = Column(String(12), nullable=False, default="monthly")
    amount = Column(Integer, nullable=False)  # In smallest currency unit
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    end_date = Column(String(10), nullable=False)
    alert_thresholds = Column(String(50), default="50,75,90,100")  # Comma-separated percentages
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category")
    alerts = relationship("BudgetAlert", back_populates="budget", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Budget {self.name} {self.period} {self.amount}>"


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    budget_id = Column(String(36), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    threshold_pct = Column(Integer, nullable=False)
    triggered_at = Column(String(30), nullable=False)
    is_read = Column(Integer, default=0, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="alerts")

    def __repr__(self):
        return f"<BudgetAlert {self.budget_id} {self.threshold_pct}%>"
