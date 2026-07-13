"""
Enum definitions used across the application.
Using Python enums + SQLite CHECK constraints (no separate lookup tables).
"""

from enum import Enum


# ── Wallet ──
class WalletType(str, Enum):
    CASH = "cash"
    SAVINGS = "savings"
    TRAVEL = "travel"
    EMERGENCY = "emergency"
    INVESTMENT = "investment"
    CUSTOM = "custom"


# ── Transaction ──
class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


# ── Category ──
class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"


# ── Budget ──
class BudgetPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# ── Goal ──
class GoalType(str, Enum):
    EMERGENCY = "emergency"
    HOUSE = "house"
    VACATION = "vacation"
    VEHICLE = "vehicle"
    EDUCATION = "education"
    RETIREMENT = "retirement"
    CUSTOM = "custom"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Fraud ──
class FraudSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ── Login ──
class LoginStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"
