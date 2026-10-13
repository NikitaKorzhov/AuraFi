from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from logger import get_logger

log = get_logger(__name__)

# Anchored to this file's directory (not the caller's cwd) so seed.py, main.py,
# and any other entry point always agree on the same database file regardless
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

# DB_NAME (and the seed credentials in seed.py) come from .env — see .env.example.
DB_PATH = str(_BASE_DIR / os.environ.get("DB_NAME", "aurafi.db"))
INIT_SQL_PATH = str(_BASE_DIR / "init.sql")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Opens a SQLite connection with foreign key enforcement turned on
    (SQLite ignores FOREIGN KEY constraints unless this is set per connection).

    Logs and re-raises on failure (bad path, permissions, locked/corrupted file)
    so a connection problem is never silently swallowed."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        log.error(f"Failed to connect to database at {db_path}: {e}")
        raise


@contextmanager
def db_connection(db_path: str = DB_PATH):
    """Opens a connection, yields it, and always closes it afterward.

    Any `sqlite3.Error` raised while the connection is in use (query errors,
    the database being locked by another process, disk I/O errors, etc.) is
    logged here before being re-raised, so every model function gets this
    handling for free just by using `with db_connection() as conn:`.
    """
    conn = get_connection(db_path)
    try:
        yield conn
    except sqlite3.Error as e:
        log.error(f"Database error on {db_path}: {e}")
        raise
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        is not None
    )


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def init_db(db_path: str = DB_PATH, sql_path: str = INIT_SQL_PATH) -> None:
    """Creates the users, transactions and budgets tables if they don't exist yet,
    by running the DDL in `init.sql`.
    """
    with db_connection(db_path) as conn:
        with open(sql_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
