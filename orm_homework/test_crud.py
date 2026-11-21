"""Homework 36, Task 6: exercise the CRUD operations on real data.

A runnable demo script (prints, not assertions) — see test_models_sqlite.py
for the actual assertion-based pytest suite (Task 10, bonus).
"""

from __future__ import annotations

import uuid

from database import SessionLocal, init_db
from models import Category
from orm_homework.crud_operations import TransactionCRUD, UserCRUD


def demo_user_crud() -> None:
    print("=== USER CRUD ===\n")
    session = SessionLocal()

    print("1) CREATE — adding a user")
    user = UserCRUD.create(session, "ivan_test", "ivan_test@test.com", "hash123")
    print(f"created: id {user.id}, {user.username}\n")

    print("2) READ — fetching the user")
    fetched = UserCRUD.get_by_username(session, "ivan_test")
    print(f"found: {fetched.username} ({fetched.email})\n")

    print("3) UPDATE — changing the email")
    updated = UserCRUD.update(session, user.id, email="ivan.new@test.com")
    print(f"updated: {updated.email}\n")

    print("4) DELETE — removing the user")
    deleted = UserCRUD.delete(session, user.id)
    print(f"deleted: {deleted}\n")

    session.close()


def demo_transaction_crud() -> None:
    print("=== TRANSACTION CRUD ===\n")
    session = SessionLocal()

    user = UserCRUD.create(session, "tx_test_user", "tx_test@test.com", "hash")
    category = Category(uuid=str(uuid.uuid4()), name="test-category", transaction_type="expense")
    session.add(category)
    session.commit()

    print("1) CREATE — adding a transaction")
    transaction = TransactionCRUD.create(session, user.id, 50.0, "expense", category.uuid, "2026-11-20")
    print(f"created: id {transaction.id}, amount {transaction.amount}\n")

    print("2) READ — fetching by user")
    for tx in TransactionCRUD.get_by_user(session, user.id):
        print(f"  - {tx}")
    print()

    print("3) DELETE — cleanup (FK order: transaction, category, user)")
    TransactionCRUD.delete(session, transaction.id)
    session.delete(category)
    session.commit()
    UserCRUD.delete(session, user.id)
    print("cleaned up\n")

    session.close()


if __name__ == "__main__":
    init_db()
    demo_user_crud()
    demo_transaction_crud()
    print("All CRUD demos completed successfully!")
