from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql

from logger import get_logger

log = get_logger(__name__)

# Anchored to this file's directory (not the caller's cwd) so seed.py, main.py,
# and any other entry point always agree on the same .env/init.sql regardless
# of where they're launched from.
_BASE_DIR = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE per line, '#' comments, no extra
    dependency). Existing environment variables always take priority over
    the file, matching standard dotenv behavior."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(_BASE_DIR / ".env")

# PostgreSQL connection settings — see .env.example. Defaults match a local
# Postgres.app/Homebrew install with trust auth (no password) on 127.0.0.1:5432.
PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB = os.environ.get("PG_DB", "aurafi")
PG_USER = os.environ.get("PG_USER", os.environ.get("USER", "postgres"))
PG_PASSWORD = os.environ.get("PG_PASSWORD", "")

INIT_SQL_PATH = str(_BASE_DIR / "init.sql")


def dsn(dbname: str | None = None) -> str:
    """libpq keyword/value DSN. `password=` is omitted entirely when empty, so
    a local trust-auth setup (e.g. Postgres.app) never sends a blank one."""
    parts = [
        f"host={PG_HOST}",
        f"port={PG_PORT}",
        f"dbname={dbname or PG_DB}",
        f"user={PG_USER}",
    ]
    if PG_PASSWORD:
        parts.append(f"password={PG_PASSWORD}")
    return " ".join(parts)


def _create_database_if_missing(dbname: str) -> None:
    """CREATE DATABASE can't run inside a transaction block and its name can't
    be a bound parameter, so this connects to the maintenance `postgres`
    database with autocommit and quotes the name via `sql.Identifier`."""
    with psycopg.connect(dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))


def get_connection(dbname: str | None = None) -> psycopg.Connection:
    """Opens a PostgreSQL connection to `dbname` (or PG_DB by default).

    Logs and re-raises on failure (bad host/port, auth failure, unknown
    database, server not running, etc.) so a connection problem is never
    silently swallowed."""
    try:
        return psycopg.connect(dsn(dbname))
    except psycopg.Error as e:
        log.error(f"Failed to connect to database {dbname or PG_DB!r}: {e}")
        raise


@contextmanager
def db_connection(dbname: str | None = None):
    """Opens a connection, yields it, and always closes it afterward.

    Any `psycopg.Error` raised while the connection is in use (query errors,
    constraint violations, the server being unreachable, etc.) is logged here
    before being re-raised, so every model function gets this handling for
    free just by using `with db_connection() as conn:`.
    """
    conn = get_connection(dbname)
    try:
        yield conn
    except psycopg.Error as e:
        log.error(f"Database error on {dbname or PG_DB!r}: {e}")
        raise
    finally:
        conn.close()


def _table_exists(conn: psycopg.Connection, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return cur.fetchone() is not None


def _table_has_column(conn: psycopg.Connection, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
            (table, column),
        )
        return cur.fetchone() is not None


def drop_all_tables(dbname: str | None = None) -> None:
    """Drops the users/categories/transactions/budgets tables (if they exist)
    so a subsequent init_db() recreates them empty. Used by seed.py to reset
    the database the same way the old SQLite path did by deleting the file."""
    _create_database_if_missing(dbname or PG_DB)
    with db_connection(dbname) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS transactions, budgets, categories, users CASCADE")
        conn.commit()


def init_db(dbname: str | None = None, sql_path: str = INIT_SQL_PATH) -> None:
    """Creates the target database if it doesn't exist yet, then creates the
    users, categories, transactions and budgets tables if they don't exist
    yet, by running the DDL in `init.sql`.
    """
    _create_database_if_missing(dbname or PG_DB)
    with db_connection(dbname) as conn:
        with open(sql_path, "r", encoding="utf-8") as f:
            with conn.cursor() as cur:
                cur.execute(f.read())
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized: {dsn()}")
