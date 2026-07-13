"""
Transaction model — the highest-volume table.
user_id is denormalized for fast user-level queries.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense', 'transfer', 'refund')",
            name="ck_txn_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'reversed', 'cancelled')",
            name="ck_txn_status",
        ),
        CheckConstraint("amount > 0", name="ck_txn_amount_positive"),
        Index("ix_txn_user_id", "user_id"),
        Index("ix_txn_wallet_id", "wallet_id"),
        Index("ix_txn_user_date", "user_id", "transaction_date"),
        Index("ix_txn_category", "category_id"),
        Index("ix_txn_type_status", "type", "status"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Denormalized user_id for direct user-level queries (avoids JOIN through wallets)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False)
    target_wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=True)  # Only for transfers
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)

    type = Column(String(10), nullable=False)
    status = Column(String(12), nullable=False, default="completed")

    # Amount always positive, stored in smallest currency unit
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")

    description = Column(Text, nullable=True)
    reference_id = Column(String(36), nullable=True)  # Links refunds to original txn

    # Recurring transaction support
    is_recurring = Column(Integer, default=0, nullable=False)
    recurring_rule = Column(Text, nullable=True)  # JSON string, parsed in Python

    transaction_date = Column(String(30), nullable=False)  # User-specified date
    created_at = Column(String(30), nullable=False)         # System timestamp
    updated_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions", foreign_keys=[wallet_id])
    target_wallet = relationship("Wallet", foreign_keys=[target_wallet_id])
    category = relationship("Category")

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount} {self.status}>"
