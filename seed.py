from __future__ import annotations

import os
from datetime import date, timedelta

from database import DB_PATH, init_db
from models import (
    add_transaction,
    check_budget_status,
    create_user,
    get_all_transactions,
    get_balance,
    get_expenses_by_category,
    set_budget,
)


# Pulled from .env (loaded as a side effect of importing database above).
# These fallbacks (used only if .env is missing) are generic placeholders,
# not real credentials — see .env.example.
SEED_USERNAME = os.environ.get("SEED_USERNAME", "demo_user")
SEED_EMAIL = os.environ.get("SEED_EMAIL", "demo@example.com")
SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")


def seed() -> int:
    """Resets the database and inserts one demo user (with a login email/password
    main.py's login prompt can be tested against) plus sample transactions and budgets."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()

    user_id = create_user(SEED_USERNAME, SEED_EMAIL, SEED_PASSWORD)

    today = date.today()
    d = lambda days_ago: (today - timedelta(days=days_ago)).isoformat()

    add_transaction(user_id, 25000.00, "income", "Salary", "Місячна зарплата", date=d(8))
    add_transaction(user_id, 450.00, "expense", "Food", "Продукти", date=d(7))
    add_transaction(user_id, 120.00, "expense", "Transport", "Проїзд", date=d(6))
    add_transaction(user_id, 2200.00, "expense", "Food", "Ресторан", date=d(4))
    add_transaction(user_id, 3000.00, "income", "Freelance", "Фріланс проєкт", date=d(3))

    set_budget(user_id, "Food", "expense", 2000.00)
    set_budget(user_id, "Transport", "expense", 500.00)

    return user_id


def print_report(user_id: int) -> None:
    print("=== Транзакції ===")
    for tx in get_all_transactions(user_id):
        signed_amount = tx["amount"] if tx["transaction_type"] == "income" else -tx["amount"]
        print(
            f"[{tx['id']}] {tx['date']} | {tx['transaction_type']:<7} | "
            f"{tx['category']:<10} | {signed_amount:>+9.2f}"
        )

    print()
    print(f"=== Баланс: {get_balance(user_id):.2f} ===")

    print()
    print("=== Витрати за категоріями ===")
    for row in get_expenses_by_category(user_id):
        print(f"{row['category']:<10} : {row['total']:.2f}")

    print()
    print("=== Статус бюджету (поточний місяць) ===")
    check_budget_status(user_id)


if __name__ == "__main__":
    uid = seed()
    print_report(uid)
    print()
    print(f"=== Login (for main.py) === email: {SEED_EMAIL} | password: {SEED_PASSWORD}")
