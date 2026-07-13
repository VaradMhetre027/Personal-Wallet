"""
Role and UserRole models — simple RBAC with 3 roles.
"""

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles", lazy="joined")

    def __repr__(self):
        return f"<UserRole user={self.user_id} role={self.role_id}>"
