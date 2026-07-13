"""
Device and LoginHistory models — security tracking.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_user_id", "user_id"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_name = Column(String(200), nullable=True)
    device_type = Column(String(20), nullable=True)   # desktop, mobile, tablet
    ip_address = Column(String(45), nullable=True)     # Supports IPv6
    user_agent = Column(Text, nullable=True)
    is_trusted = Column(Integer, default=0, nullable=False)
    last_login_at = Column(String(30), nullable=False)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="devices")
    login_history = relationship("LoginHistory", back_populates="device")

    def __repr__(self):
        return f"<Device {self.device_name} ({self.device_type})>"


class LoginHistory(Base):
    __tablename__ = "login_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed', 'locked')",
            name="ck_login_status",
        ),
        Index("ix_login_user_id", "user_id"),
        Index("ix_login_user_created", "user_id", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(10), nullable=False)  # success, failed, locked
    failure_reason = Column(String(50), nullable=True)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user = relationship("User", back_populates="login_history")
    device = relationship("Device", back_populates="login_history")

    def __repr__(self):
        return f"<LoginHistory {self.user_id} {self.status}>"
