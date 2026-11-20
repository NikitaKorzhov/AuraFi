"""Homework 30, Task 6: JOIN queries across users / transactions / categories."""

from __future__ import annotations

import uuid

import psycopg

from postgres.connection import get_db_cursor


def _seed(cur) -> tuple[int, int]:
    cur.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
        ("join_alice", "join_alice@example.com", "hash"),
    )
    alice_id = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
        ("join_bob", "join_bob@example.com", "hash"),
    )
    bob_id = cur.fetchone()[0]

    food_uuid, transport_uuid = str(uuid.uuid4()), str(uuid.uuid4())
    cur.execute(
        "INSERT INTO categories (uuid, name, transaction_type) VALUES (%s, %s, 'expense'), (%s, %s, 'expense');",
        (food_uuid, "Food", transport_uuid, "Transport"),
    )

    cur.execute(
        """
        INSERT INTO transactions (amount, transaction_type, category_uuid, date, user_id) VALUES
            (100, 'expense', %s, '2026-11-01', %s),
            (50,  'expense', %s, '2026-11-02', %s),
            (30,  'expense', %s, '2026-11-03', %s);
        """,
        (food_uuid, alice_id, transport_uuid, alice_id, food_uuid, bob_id),
    )
    return alice_id, bob_id


def demonstrate_joins() -> None:
    print("=== JOIN QUERIES ===\n")

    print("1) Seeding test data:")
    with get_db_cursor() as cur:
        _seed(cur)
    print("Data inserted\n")

    print("2) INNER JOIN — users with their transactions and category names:")
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT u.username, c.name, t.amount
            FROM users u
            INNER JOIN transactions t ON u.id = t.user_id
            INNER JOIN categories c ON t.category_uuid = c.uuid
            WHERE u.username IN ('join_alice', 'join_bob')
            ORDER BY u.username, t.date;
            """
        )
        for username, category, amount in cur.fetchall():
            print(f"  {username}: {amount} [{category}]")
    print()

    print("3) LEFT JOIN — every user, even those with zero transactions:")
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT u.username, COUNT(t.id) AS tx_count
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            WHERE u.username IN ('join_alice', 'join_bob')
            GROUP BY u.id, u.username
            ORDER BY u.username;
            """
        )
        for username, count in cur.fetchall():
            print(f"  {username}: {count} transactions")
    print()

    print("4) Aggregation — total spend per user:")
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT u.username, COALESCE(SUM(t.amount), 0) AS total_spent
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            WHERE u.username IN ('join_alice', 'join_bob')
            GROUP BY u.id, u.username
            ORDER BY total_spent DESC;
            """
        )
        for username, total in cur.fetchall():
            print(f"  {username}: total spent {total}")


if __name__ == "__main__":
    try:
        demonstrate_joins()
    except psycopg.Error as e:
        print(f"Error: {e}")
