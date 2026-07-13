"""
Wallet model — multiple wallets per user with integer-cent balances.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint(
            "wallet_type IN ('cash', 'savings', 'travel', 'emergency', 'investment', 'custom')",
            name="ck_wallet_type",
        ),
        Index("ix_wallets_user_id", "user_id"),
        Index("ix_wallets_user_type", "user_id", "wallet_type"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    wallet_type = Column(String(20), nullable=False, default="cash")
    currency = Column(String(3), nullable=False, default="INR")

    # Balance in smallest currency unit (paise/cents) — avoids floating-point errors
    balance = Column(Integer, nullable=False, default=0)

    is_frozen = Column(Integer, default=0, nullable=False)
    is_default = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallets")
    transactions = relationship(
        "Transaction",
        back_populates="wallet",
        foreign_keys="Transaction.wallet_id",
    )

    def __repr__(self):
        return f"<Wallet {self.name} ({self.wallet_type}) balance={self.balance}>"
