"""Homework 30, Task 9 (bonus): inspect the schema via information_schema."""

from __future__ import annotations

from postgres.connection import get_db_cursor


def analyze_database() -> None:
    print("=== SCHEMA ANALYSIS ===\n")

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
        )
        tables = [row[0] for row in cur.fetchall()]

        for table_name in tables:
            print(f"Table: {table_name}")
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
            )
            for col_name, data_type, is_nullable in cur.fetchall():
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"    - {col_name}: {data_type} [{nullable}]")
            print()


if __name__ == "__main__":
    analyze_database()
