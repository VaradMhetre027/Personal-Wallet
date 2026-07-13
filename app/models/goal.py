"""
Goal and GoalContribution models — Phase 2 API, schema defined now.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "goal_type IN ('emergency', 'house', 'vacation', 'vehicle', 'education', 'retirement', 'custom')",
            name="ck_goal_type",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'cancelled')",
            name="ck_goal_status",
        ),
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_goal_priority"),
        Index("ix_goals_user_id", "user_id"),
        Index("ix_goals_user_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    goal_type = Column(String(15), nullable=False, default="custom")
    target_amount = Column(Integer, nullable=False)  # In smallest currency unit
    current_amount = Column(Integer, nullable=False, default=0)  # Denormalized sum of contributions
    currency = Column(String(3), default="INR", nullable=False)
    target_date = Column(String(10), nullable=True)  # YYYY-MM-DD, optional deadline
    priority = Column(Integer, default=1, nullable=False)
    status = Column(String(12), default="active", nullable=False)
    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="goals")
    contributions = relationship("GoalContribution", back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Goal {self.name} {self.current_amount}/{self.target_amount}>"


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    goal_id = Column(String(36), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=True)  # Nullable for manual entries
    amount = Column(Integer, nullable=False)  # Can be negative for withdrawals
    note = Column(Text, nullable=True)
    contributed_at = Column(String(30), nullable=False)
    created_at = Column(String(30), nullable=False)

    # Relationships
    goal = relationship("Goal", back_populates="contributions")
    wallet = relationship("Wallet")

    def __repr__(self):
        return f"<GoalContribution {self.goal_id} {self.amount}>"
