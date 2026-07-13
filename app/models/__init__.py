"""
Models package — imports all models so Alembic can discover them.
"""

from app.models.user import User
from app.models.role import Role, UserRole
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.budget import Budget, BudgetAlert
from app.models.goal import Goal, GoalContribution
from app.models.device import Device, LoginHistory
from app.models.audit import AuditLog
from app.models.fraud import FraudFlag
from app.models.notification import Notification

__all__ = [
    "User",
    "Role",
    "UserRole",
    "Wallet",
    "Transaction",
    "Category",
    "Budget",
    "BudgetAlert",
    "Goal",
    "GoalContribution",
    "Device",
    "LoginHistory",
    "AuditLog",
    "FraudFlag",
    "Notification",
]
