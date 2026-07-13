"""
FraudFlag model — rule-based anomaly detection flags.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class FraudFlag(Base):
    __tablename__ = "fraud_flags"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_fraud_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'dismissed')",
            name="ck_fraud_status",
        ),
        Index("ix_fraud_user_id", "user_id"),
        Index("ix_fraud_status", "status"),
        Index("ix_fraud_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)
    rule_code = Column(String(50), nullable=False)  # rapid_transactions, unusual_amount, etc.
    severity = Column(String(10), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(15), default="open", nullable=False)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(String(30), nullable=True)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    transaction = relationship("Transaction")
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<FraudFlag {self.rule_code} {self.severity}>"
