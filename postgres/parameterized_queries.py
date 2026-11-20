"""Homework 30, Task 5: parameterized queries vs. SQL injection."""

from __future__ import annotations

import psycopg

from postgres.connection import get_db_cursor


def demonstrate_sql_injection() -> None:
    print("=== PARAMETERIZED QUERIES ===\n")

    print("1) Inserting test data:")
    with get_db_cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
            ("alice_wonderland", "alice@example.com", "hash"),
        )
    print("Inserted: alice_wonderland\n")

    print("2) SAFE lookup by username (parameterized):")
    search_username = "alice_wonderland"
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id, username, email FROM users WHERE username = %s;",
            (search_username,),
        )
        print(f"Found: {cur.fetchone()}\n")

    print("3) UNSAFE code (illustration only — never run this):")
    dangerous_username = "admin'; DROP TABLE users; --"
    dangerous_query = f"SELECT * FROM users WHERE username = '{dangerous_username}';"
    print(f"   {dangerous_query}")
    print("   ^ string-concatenated like this, that literal input drops the table\n")

    print("   The parameterized form, called with the exact same input:")
    print("   cur.execute(\"SELECT * FROM users WHERE username = %s;\", (dangerous_username,))")
    print("   ^ psycopg sends it as DATA, not SQL — it just finds no matching username, safely\n")

    print("4) Multi-parameter UPDATE and DELETE:")
    with get_db_cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
            ("bob_builder", "bob@example.com", "hash"),
        )
    with get_db_cursor() as cur:
        cur.execute(
            "UPDATE users SET email = %s WHERE username = %s;",
            ("bob.new@example.com", "bob_builder"),
        )
    print("Updated: bob_builder -> bob.new@example.com")
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM users WHERE username = %s;", ("bob_builder",))
    print("Deleted: bob_builder\n")


if __name__ == "__main__":
    try:
        demonstrate_sql_injection()
    except psycopg.Error as e:
        print(f"Error: {e}")
