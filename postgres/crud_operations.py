"""Homework 30, Task 4: CRUD operations against AuraFi's real schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psycopg

from postgres.connection import get_db_cursor


@dataclass
class User:
    id: int
    username: str
    email: str


class UserRepository:
    """Create/Read/Update/Delete for the `users` table."""

    def create(self, username: str, email: str, password_hash: str) -> Optional[int]:
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                    (username, email, password_hash),
                )
                return cur.fetchone()[0]
        except psycopg.errors.UniqueViolation:
            print(f"Error: a user with username={username!r} or email={email!r} already exists")
            return None

    def read(self, user_id: int) -> Optional[User]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, username, email FROM users WHERE id = %s;", (user_id,))
            row = cur.fetchone()
            return User(*row) if row else None

    def read_all(self) -> list[User]:
        with get_db_cursor() as cur:
            cur.execute("SELECT id, username, email FROM users ORDER BY id;")
            return [User(*row) for row in cur.fetchall()]

    def update_email(self, user_id: int, email: str) -> bool:
        with get_db_cursor() as cur:
            cur.execute("UPDATE users SET email = %s WHERE id = %s;", (email, user_id))
            return cur.rowcount > 0

    def delete(self, user_id: int) -> bool:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            return cur.rowcount > 0


@dataclass
class Transaction:
    id: int
    amount: float
    transaction_type: str
    category_uuid: str
    date: str


class TransactionRepository:
    """Create/Read/Delete for the `transactions` table (no update: a
    transaction is replaced, not edited, matching the rest of AuraFi)."""

    def create(
        self, user_id: int, amount: float, transaction_type: str, category_uuid: str, date: str
    ) -> int:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (amount, transaction_type, category_uuid, date, user_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (amount, transaction_type, category_uuid, date, user_id),
            )
            return cur.fetchone()[0]

    def read_all_for_user(self, user_id: int) -> list[Transaction]:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, amount, transaction_type, category_uuid, date
                FROM transactions WHERE user_id = %s ORDER BY date;
                """,
                (user_id,),
            )
            return [Transaction(*row) for row in cur.fetchall()]

    def delete(self, transaction_id: int) -> bool:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE id = %s;", (transaction_id,))
            return cur.rowcount > 0


if __name__ == "__main__":
    import uuid

    users = UserRepository()
    transactions = TransactionRepository()

    print("=== CRUD OPERATIONS ===\n")

    print("CREATE — adding users:")
    user_id_1 = users.create("ivan_petrov", "ivan@example.com", "hash1")
    user_id_2 = users.create("maria_sidorenko", "maria@example.com", "hash2")
    print(f"Users created: id {user_id_1}, {user_id_2}\n")

    print("READ — fetching one user:")
    user = users.read(user_id_1)
    print(f"{user.username}: {user.email}\n")

    print("READ ALL — fetching every user:")
    for u in users.read_all():
        print(f"  - {u.username} ({u.email})")
    print()

    print("UPDATE — changing an email:")
    print(f"updated: {users.update_email(user_id_1, 'newemail@example.com')}\n")

    print("CREATE a transaction tied to that user (needs a category first):")
    category_uuid = str(uuid.uuid4())
    with get_db_cursor() as cur:
        cur.execute(
            "INSERT INTO categories (uuid, name, transaction_type) VALUES (%s, %s, %s);",
            (category_uuid, "Food", "expense"),
        )
    tx_id = transactions.create(user_id_1, 42.50, "expense", category_uuid, "2026-11-15")
    print(f"transaction created: id {tx_id}")
    for tx in transactions.read_all_for_user(user_id_1):
        print(f"  - [{tx.id}] {tx.date} {tx.transaction_type} {tx.amount}")
    print()

    print("DELETE — removing a user:")
    print(f"deleted: {users.delete(user_id_2)}\n")

    print("Final user list:")
    for u in users.read_all():
        print(f"  - {u.username} ({u.email})")
