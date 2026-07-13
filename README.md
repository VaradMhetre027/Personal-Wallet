# Personal-Wallet
Production-grade personal finance API built with FastAPI &amp; SQLite — JWT auth with 2FA, multi-wallet management, transaction tracking, and full audit logging.
# Personal Wallet Management Platform

A production-grade personal finance management system built with **FastAPI** + **SQLite**.

## Features (Phase 1)

- 🔐 **Authentication** — JWT access/refresh tokens, bcrypt password hashing, TOTP 2FA, device tracking, brute-force protection
- 💰 **Wallets** — Multiple wallets (cash, savings, travel, etc.), freeze/unfreeze, inter-wallet transfers
- 💳 **Transactions** — Income/expense tracking, reversal, CSV/Excel export, multi-field filtering
- 📂 **Categories** — 25 default categories + custom user categories
- 📊 **Audit Logging** — Every state change is recorded

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.13+, FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (WAL mode) |
| Auth | JWT (python-jose), bcrypt, TOTP (pyotp) |
| Validation | Pydantic V2 |
| Migrations | Alembic |

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
copy .env.example .env
# Edit .env and set a strong SECRET_KEY

# 4. Run the server
uvicorn main:app --reload

# 5. Open API docs
# http://localhost:8000/docs
```

## Project Structure

```
Personal Wallet/
├── app/
│   ├── __init__.py          # FastAPI app factory
│   ├── api/
│   │   ├── auth/            # Authentication module
│   │   ├── wallets/         # Wallet management
│   │   ├── transactions/    # Transaction processing
│   │   └── categories/      # Category management
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── database.py      # SQLAlchemy engine + session
│   │   ├── security.py      # JWT, bcrypt, TOTP utilities
│   │   ├── dependencies.py  # FastAPI auth dependencies
│   │   ├── exceptions.py    # Custom exception classes
│   │   ├── enums.py         # Domain enums
│   │   └── seeder.py        # Default data seeder
│   └── models/
│       ├── user.py          # User model
│       ├── role.py          # Role + UserRole models
│       ├── wallet.py        # Wallet model
│       ├── transaction.py   # Transaction model
│       ├── category.py      # Category model + defaults
│       ├── budget.py        # Budget + BudgetAlert (Phase 2)
│       ├── goal.py          # Goal + GoalContribution (Phase 2)
│       ├── device.py        # Device + LoginHistory
│       ├── audit.py         # AuditLog
│       ├── fraud.py         # FraudFlag (Phase 4)
│       └── notification.py  # Notification (Phase 3)
├── main.py                  # Entry point
├── requirements.txt
├── .env                     # Environment variables (not committed)
├── .env.example
└── .gitignore
```

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` — Create account
- `POST /login` — Get JWT tokens
- `POST /logout` — Invalidate refresh token
- `POST /refresh` — Refresh access token
- `GET /me` — Get profile
- `PUT /me` — Update profile
- `PUT /change-password` — Change password
- `POST /forgot-password` — Request reset token
- `POST /reset-password` — Reset password

### Wallets (`/api/v1/wallets`)
- `GET /` — List wallets
- `POST /` — Create wallet
- `GET /{id}` — Get wallet
- `PUT /{id}` — Update wallet
- `DELETE /{id}` — Delete wallet
- `POST /{id}/freeze` — Freeze wallet
- `POST /{id}/unfreeze` — Unfreeze wallet
- `POST /transfer` — Transfer between wallets

### Transactions (`/api/v1/transactions`)
- `GET /` — List (with filters)
- `POST /` — Create
- `GET /export` — Export CSV/Excel
- `GET /{id}` — Get detail
- `PUT /{id}` — Update
- `DELETE /{id}` — Cancel
- `POST /{id}/reverse` — Reverse

### Categories (`/api/v1/categories`)
- `GET /` — List all
- `POST /` — Create custom
- `PUT /{id}` — Update
- `DELETE /{id}` — Deactivate

## Financial Amounts

All monetary values are stored and transmitted as **integers in the smallest currency unit** (paise for INR, cents for USD). For example:
- ₹199.50 → `19950`
- $25.00 → `2500`

This avoids floating-point precision errors. The API response includes both `amount` (integer) and `amount_formatted` (human-readable string like "₹199.50").

## Security

- Passwords hashed with bcrypt (cost factor 12)
- JWT access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Account locks after 5 failed login attempts
- TOTP-based 2FA (Google Authenticator compatible)
- All state changes logged to audit_logs table
- SQLite file excluded from version control
