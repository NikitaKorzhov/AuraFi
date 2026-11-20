from __future__ import annotations

import os

import database  # import side effect: loads .env into os.environ, same as the SQLite path

PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
# Deliberately its own env var/default, distinct from the live app's PG_DB
# (database.py) — the live app also runs against a real `aurafi` Postgres
# database now, so sharing PG_DB here would mean this homework's demo
# INSERT/UPDATE/DELETE/ROLLBACK scripts mutate the same rows the app uses.
PG_DB = os.environ.get("PG_HOMEWORK_DB", "aurafi_homework30")
PG_USER = os.environ.get("PG_USER", os.environ.get("USER", "postgres"))
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")


def dsn(dbname: str | None = None) -> str:
    """libpq keyword/value DSN. `password=` is omitted entirely when empty,
    so a local trust-auth setup (e.g. Postgres.app) never sends a blank one."""
    parts = [
        f"host={PG_HOST}",
        f"port={PG_PORT}",
        f"dbname={dbname or PG_DB}",
        f"user={PG_USER}",
    ]
    if PG_PASSWORD:
        parts.append(f"password={PG_PASSWORD}")
    return " ".join(parts)
