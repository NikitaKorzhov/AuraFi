"""Homework 30, Task 7: transactions, COMMIT, and ROLLBACK.

Named transactions_demo.py (not transactions.py) to avoid colliding with the
app's own `transactions` *table* name when read out loud in this package.
"""

from __future__ import annotations

import psycopg

from postgres.connection import get_db_connection


def demonstrate_transactions() -> None:
    print("=== TRANSACTIONS ===\n")

    print("1) Successful transaction (two inserts, one COMMIT):")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                    ("charlie", "charlie@example.com", "hash"),
                )
                user_id = cur.fetchone()[0]
                print("  step 1: user added")

                cur.execute(
                    "INSERT INTO categories (uuid, name, transaction_type) VALUES (%s, %s, 'income') ON CONFLICT DO NOTHING;",
                    ("salary-demo", "Salary"),
                )
                cur.execute(
                    "INSERT INTO transactions (amount, transaction_type, category_uuid, date, user_id) "
                    "VALUES (%s, 'income', %s, %s, %s);",
                    (1000, "salary-demo", "2026-11-15", user_id),
                )
                print("  step 2: transaction added")

                conn.commit()
                print("  step 3: COMMIT — both operations saved\n")
    except psycopg.Error as e:
        print(f"  Error: {e}\n")

    print("2) Failing transaction (duplicate email -> ROLLBACK):")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        ("david", "david@example.com", "hash"),
                    )
                    print("  step 1: user 'david' added")

                    cur.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
                        ("eve", "david@example.com", "hash"),  # duplicate email on purpose
                    )
                    conn.commit()

                except psycopg.errors.UniqueViolation as e:
                    conn.rollback()
                    print(f"  uniqueness error: {e}".splitlines()[0])
                    print("  ROLLBACK — both operations undone\n")
    except psycopg.Error as e:
        print(f"  Connection error: {e}\n")

    print("3) Checking the result:")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, email FROM users WHERE username IN ('charlie', 'david', 'eve') ORDER BY username;"
            )
            rows = cur.fetchall()
            if rows:
                print("  Users in the db:")
                for username, email in rows:
                    print(f"    - {username}: {email}")
                print("\n  charlie was added successfully")
                print("  david and eve were NOT added (ROLLBACK took effect)")
            else:
                print("  No users found")


if __name__ == "__main__":
    demonstrate_transactions()
