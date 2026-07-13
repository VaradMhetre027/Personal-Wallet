"""
Notification model — in-app notifications, polled by frontend.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notif_user_id", "user_id"),
        Index("ix_notif_user_unread", "user_id", "is_read"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)  # budget_alert, goal_milestone, security_alert, etc.
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Integer, default=0, nullable=False)
    action_url = Column(String(500), nullable=True)  # Deep link to relevant frontend page
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type}: {self.title}>"
