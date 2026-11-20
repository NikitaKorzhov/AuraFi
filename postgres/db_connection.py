"""Homework 30, Task 2: first connection to PostgreSQL from Python."""

from __future__ import annotations

import psycopg

from postgres.config import dsn

if __name__ == "__main__":
    try:
        with psycopg.connect(dsn("postgres")) as conn:
            print("Connected to PostgreSQL successfully!")

            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                print(f"\nPostgreSQL version:\n{cur.fetchone()[0]}\n")

                cur.execute("SELECT current_user;")
                print(f"User: {cur.fetchone()[0]}")

                cur.execute("SELECT current_database();")
                print(f"Current db: {cur.fetchone()[0]}")

    except psycopg.Error as e:
        print(f"Connection error: {e}")
