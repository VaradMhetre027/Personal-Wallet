"""
User model — central user record.
UUIDs as TEXT for SQLite compatibility.
"""

from sqlalchemy import Column, String, Integer, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import generate_uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), unique=True, nullable=True)

    # Account status
    is_active = Column(Integer, default=1, nullable=False)       # 0/1 boolean for SQLite
    is_verified = Column(Integer, default=1, nullable=False)     # Auto-verified in local dev

    # 2FA
    totp_secret = Column(Text, nullable=True)
    is_2fa_enabled = Column(Integer, default=0, nullable=False)

    # Brute-force protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(String(30), nullable=True)  # ISO 8601 datetime

    # Refresh token (hashed)
    refresh_token_hash = Column(Text, nullable=True)

    # Timestamps (TEXT for SQLite — ISO 8601 strings)
    created_at = Column(String(30), nullable=False)
    updated_at = Column(String(30), nullable=False)

    # ── Relationships ──
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", lazy="joined")
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", foreign_keys="Transaction.user_id")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
