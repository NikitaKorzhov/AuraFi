"""Homework 36, Task 8: raw SQL vs SQLAlchemy ORM, side by side.

The real migration already happened in place, in the live models.py (see its
module docstring) — this file exists purely to satisfy the "Створена
міграція з SQL на ORM" checklist item with a direct, side-by-side comparison
of the exact same four operations, old way vs new way.
"""

from __future__ import annotations

import inspect

import psycopg

import database
import models
from models import SessionLocal, Transaction, User


# ❌ OLD WAY — raw SQL via psycopg


def old_add_user_sql(username: str, email: str, password_hash: str) -> None:
    """SQL version."""
    with psycopg.connect(database.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash),
            )
        conn.commit()
    print(f"SQL: user {username} added")


def old_get_users_sql() -> list[dict]:
    """SQL version."""
    with psycopg.connect(database.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email FROM users")
            rows = cur.fetchall()
    return [{"id": row[0], "username": row[1], "email": row[2]} for row in rows]


def old_update_user_sql(user_id: int, email: str) -> None:
    """SQL version."""
    with psycopg.connect(database.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))
        conn.commit()
    print(f"SQL: user {user_id} updated")


def old_get_user_transactions_sql(user_id: int) -> list[tuple]:
    """SQL version, with a JOIN."""
    with psycopg.connect(database.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.username, t.amount, t.transaction_type
                FROM users u
                LEFT JOIN transactions t ON u.id = t.user_id
                WHERE u.id = %s
                """,
                (user_id,),
            )
            return cur.fetchall()


# ✅ NEW WAY — SQLAlchemy ORM


def new_add_user_orm(username: str, email: str, password_hash: str) -> int:
    """ORM version."""
    with SessionLocal() as session:
        user = User(username=username, email=email, password_hash=password_hash)
        session.add(user)
        session.commit()
        print(f"ORM: user {username} added")
        return user.id


def new_get_users_orm() -> list[dict]:
    """ORM version."""
    with SessionLocal() as session:
        users = session.query(User).all()
        return [{"id": u.id, "username": u.username, "email": u.email} for u in users]


def new_update_user_orm(user_id: int, email: str) -> None:
    """ORM version."""
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            user.email = email
            session.commit()
    print(f"ORM: user {user_id} updated")


def new_get_user_transactions_orm(user_id: int) -> list[tuple]:
    """ORM version — transactions arrive through `user.transactions`, no
    JOIN written by hand."""
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            return []
        return [(user.username, tx.amount, tx.transaction_type) for tx in user.transactions]


def _line_count(func_) -> int:
    return len(inspect.getsource(func_).rstrip().splitlines())


if __name__ == "__main__":
    print("=== COMPARISON: SQL vs ORM ===\n")

    pairs = [
        ("ADD USER", old_add_user_sql, new_add_user_orm),
        ("GET USERS", old_get_users_sql, new_get_users_orm),
        ("UPDATE USER", old_update_user_sql, new_update_user_orm),
        ("GET USER TRANSACTIONS (JOIN)", old_get_user_transactions_sql, new_get_user_transactions_orm),
    ]

    for i, (label, old_fn, new_fn) in enumerate(pairs, start=1):
        old_lines, new_lines = _line_count(old_fn), _line_count(new_fn)
        saved_pct = round(100 * (1 - new_lines / old_lines))
        print(f"{i}. {label}")
        print(f"   SQL: {old_lines} lines (manual connection/cursor management)")
        print(f"   ORM: {new_lines} lines")
        print(f"   Savings: {saved_pct}%\n")

    print("Running both versions against the real database to confirm they agree:\n")

    database.init_db()
    old_add_user_sql("migration_demo_sql", "migration_demo_sql@example.com", "hash")
    new_user_id = new_add_user_orm("migration_demo_orm", "migration_demo_orm@example.com", "hash")

    print("\nSQL read:", [u for u in old_get_users_sql() if u["username"].startswith("migration_demo")])
    print("ORM read:", [u for u in new_get_users_orm() if u["username"].startswith("migration_demo")])

    new_update_user_orm(new_user_id, "migration_demo_orm_updated@example.com")

    # cleanup — leave the real database exactly as it was
    with models.SessionLocal() as session:
        for user in session.query(User).filter(User.username.like("migration_demo%")).all():
            session.delete(user)
        session.commit()
    print("\ncleaned up demo rows")
