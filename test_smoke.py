"""
End-to-end API smoke test.
Tests: Register -> Login -> Create Wallet -> Create Transaction -> List -> Export
"""

import httpx
import json
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8000/api/v1"
client = httpx.Client(base_url=BASE, timeout=10)
errors = []


def test(name, response, expected_status):
    ok = response.status_code == expected_status
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} -> {response.status_code}")
    if not ok:
        errors.append(f"{name}: expected {expected_status}, got {response.status_code}")
        try:
            print(f"         Detail: {response.json()}")
        except Exception:
            print(f"         Body: {response.text[:200]}")
    return ok


print("=" * 60)
print("PERSONAL WALLET API - END-TO-END SMOKE TEST")
print("=" * 60)

# 1. Register
print("\n[1] AUTHENTICATION")
r = client.post("/auth/register", json={
    "email": "test@example.com",
    "username": "testuser",
    "password": "StrongPass123!",
    "full_name": "Test User",
})
test("Register user", r, 201)
try:
    user_data = r.json()
except Exception:
    user_data = {}
print(f"         User ID: {user_data.get('id', 'N/A')}")

# 2. Login
r = client.post("/auth/login", json={
    "email": "test@example.com",
    "password": "StrongPass123!",
})
test("Login", r, 200)
try:
    tokens = r.json()
except Exception:
    tokens = {}
access_token = tokens.get("access_token", "")
print(f"         Token type: {tokens.get('token_type')}, expires_in: {tokens.get('expires_in')}s")

# Set auth header
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Get profile
r = client.get("/auth/me", headers=headers)
test("Get profile", r, 200)

# 4. Login history
r = client.get("/auth/login-history", headers=headers)
test("Login history", r, 200)
print(f"         Login entries: {len(r.json())}")

# 5. Devices
r = client.get("/auth/devices", headers=headers)
test("List devices", r, 200)
print(f"         Devices tracked: {len(r.json())}")

# ── WALLETS ──
print("\n[2] WALLETS")

r = client.post("/wallets", json={
    "name": "My Cash Wallet",
    "wallet_type": "cash",
    "currency": "INR",
    "is_default": True,
}, headers=headers)
test("Create cash wallet", r, 201)
wallet1 = r.json()
wallet1_id = wallet1.get("id", "")
print(f"         Wallet ID: {wallet1_id}, Balance: {wallet1.get('balance_formatted')}")

r = client.post("/wallets", json={
    "name": "Savings Account",
    "wallet_type": "savings",
    "currency": "INR",
}, headers=headers)
test("Create savings wallet", r, 201)
wallet2 = r.json()
wallet2_id = wallet2.get("id", "")

r = client.get("/wallets", headers=headers)
test("List wallets", r, 200)
summary = r.json()
print(f"         Total wallets: {summary.get('wallet_count')}, Total balance: {summary.get('total_balance_formatted')}")

# ── CATEGORIES ──
print("\n[3] CATEGORIES")

r = client.get("/categories", headers=headers)
test("List categories", r, 200)
categories = r.json()
print(f"         Total categories: {len(categories)}")

# Find "Salary" category for income
salary_cat = next((c for c in categories if c["name"] == "Salary"), None)
food_cat = next((c for c in categories if c["name"] == "Food & Dining"), None)

r = client.post("/categories", json={
    "name": "Gym Membership",
    "type": "expense",
    "color": "#FF5733",
}, headers=headers)
test("Create custom category", r, 201)

# ── TRANSACTIONS ──
print("\n[4] TRANSACTIONS")

# Add income
r = client.post("/transactions", json={
    "wallet_id": wallet1_id,
    "category_id": salary_cat["id"] if salary_cat else None,
    "type": "income",
    "amount": 5000000,  # 50,000.00 INR
    "description": "June Salary",
    "transaction_date": "2026-06-01T09:00:00",
}, headers=headers)
test("Add income (salary)", r, 201)
income_txn = r.json()
print(f"         Amount: {income_txn.get('amount_formatted')}, Category: {income_txn.get('category_name')}")

# Check wallet balance updated
r = client.get(f"/wallets/{wallet1_id}", headers=headers)
test("Wallet balance after income", r, 200)
print(f"         New balance: {r.json().get('balance_formatted')}")

# Add expense
r = client.post("/transactions", json={
    "wallet_id": wallet1_id,
    "category_id": food_cat["id"] if food_cat else None,
    "type": "expense",
    "amount": 75000,  # 750.00 INR
    "description": "Restaurant dinner",
    "transaction_date": "2026-06-15T20:00:00",
}, headers=headers)
test("Add expense (food)", r, 201)

# Add another expense
r = client.post("/transactions", json={
    "wallet_id": wallet1_id,
    "type": "expense",
    "amount": 200000,  # 2,000.00 INR
    "description": "Grocery shopping",
    "transaction_date": "2026-06-16T11:00:00",
}, headers=headers)
test("Add expense (grocery)", r, 201)

# List transactions
r = client.get("/transactions", headers=headers)
test("List all transactions", r, 200)
txn_list = r.json()
print(f"         Total: {txn_list.get('total')}, Income: {txn_list.get('total_income')}, Expense: {txn_list.get('total_expense')}")
print(f"         Net: {txn_list.get('net_formatted')}")

# Filter by type
r = client.get("/transactions?type=expense", headers=headers)
test("Filter expenses only", r, 200)
print(f"         Expense count: {r.json().get('total')}")

# ── WALLET TRANSFER ──
print("\n[5] WALLET TRANSFER")

r = client.post("/wallets/transfer", json={
    "from_wallet_id": wallet1_id,
    "to_wallet_id": wallet2_id,
    "amount": 1000000,  # 10,000.00 INR
    "description": "Monthly savings",
}, headers=headers)
test("Transfer between wallets", r, 200)
transfer = r.json()
print(f"         Transferred: {transfer.get('amount_formatted')}")
print(f"         From balance: {transfer.get('from_wallet', {}).get('balance_formatted')}")
print(f"         To balance: {transfer.get('to_wallet', {}).get('balance_formatted')}")

# ── WALLET FREEZE ──
print("\n[6] WALLET FREEZE/UNFREEZE")

r = client.post(f"/wallets/{wallet2_id}/freeze", headers=headers)
test("Freeze savings wallet", r, 200)
print(f"         Frozen: {r.json().get('is_frozen')}")

# Try transaction on frozen wallet (should fail)
r = client.post("/transactions", json={
    "wallet_id": wallet2_id,
    "type": "expense",
    "amount": 100,
    "description": "Should fail",
}, headers=headers)
test("Transaction on frozen wallet (expect 403)", r, 403)

r = client.post(f"/wallets/{wallet2_id}/unfreeze", headers=headers)
test("Unfreeze savings wallet", r, 200)

# ── TRANSACTION REVERSAL ──
print("\n[7] TRANSACTION REVERSAL")

r = client.post(f"/transactions/{income_txn['id']}/reverse", headers=headers)
test("Reverse salary transaction", r, 200)
reversal = r.json()
print(f"         Reversal type: {reversal.get('type')}, Amount: {reversal.get('amount_formatted')}")

# ── EXPORT ──
print("\n[8] EXPORT")

r = client.get("/transactions/export?format=csv", headers=headers)
test("Export CSV", r, 200)
print(f"         Content-Type: {r.headers.get('content-type')}")
print(f"         CSV lines: {len(r.text.strip().splitlines())}")

r = client.get("/transactions/export?format=excel", headers=headers)
test("Export Excel", r, 200)
print(f"         Content-Type: {r.headers.get('content-type')}")
print(f"         Excel size: {len(r.content)} bytes")

# ── SUMMARY ──
print("\n" + "=" * 60)
if errors:
    print(f"RESULT: {len(errors)} FAILURES")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("RESULT: ALL TESTS PASSED")
    sys.exit(0)
