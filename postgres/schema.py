"""Homework 30, Task 3: create the database and tables (with PK/FK) for
AuraFi's actual domain — users / categories / transactions / budgets."""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg import sql

from postgres.config import PG_DB, dsn

_SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"


def create_database(db_name: str = PG_DB) -> None:
    """Creates `db_name` on the server if it doesn't already exist.

    CREATE DATABASE can't run inside a transaction block and its name can't
    be a query parameter, so this connects with autocommit and uses
    `sql.Identifier` to quote the name safely instead of an f-string.
    """
    with psycopg.connect(dsn("postgres")) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                print(f"Database '{db_name}' created")
            else:
                print(f"Database '{db_name}' already exists")


def create_tables(db_name: str = PG_DB) -> None:
    with psycopg.connect(dsn(db_name)) as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
        conn.commit()
        print("Tables users, categories, transactions, budgets created")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )
            tables = [row[0] for row in cur.fetchall()]
            print(f"Tables in db: {', '.join(sorted(tables))}")


if __name__ == "__main__":
    try:
        create_database()
        create_tables()
    except psycopg.Error as e:
        print(f"Error: {e}")
