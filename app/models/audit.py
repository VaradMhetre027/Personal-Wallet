"""
AuditLog model — comprehensive audit trail for all state-changing operations.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # NULL for system events
    action = Column(String(100), nullable=False)  # e.g., "wallet.create", "txn.create"
    entity_type = Column(String(50), nullable=False)  # user, wallet, transaction, budget, goal
    entity_id = Column(String(36), nullable=True)
    old_value = Column(Text, nullable=True)  # JSON string of previous state
    new_value = Column(Text, nullable=True)  # JSON string of new state
    ip_address = Column(String(45), nullable=True)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
