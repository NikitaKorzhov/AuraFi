from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from logger import get_logger

log = get_logger(__name__)

# Anchored to this file's directory (not the caller's cwd) so seed.py, main.py,
# and any other entry point always agree on the same .env regardless of where
# they're launched from.
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


def dsn(dbname: str | None = None) -> str:
    """libpq keyword/value DSN — still used by the raw-psycopg admin helper
    below. CREATE DATABASE can't run through a SQLAlchemy Session (it can't
    run inside a transaction block, and a session is bound to one already-
    connected database), so creating/checking databases stays on psycopg."""
    parts = [
        f"host={PG_HOST}",
        f"port={PG_PORT}",
        f"dbname={dbname or PG_DB}",
        f"user={PG_USER}",
    ]
    if PG_PASSWORD:
        parts.append(f"password={PG_PASSWORD}")
    return " ".join(parts)


def database_url(dbname: str | None = None) -> str:
    """SQLAlchemy engine URL for `dbname` (or PG_DB by default). Uses the
    `postgresql+psycopg` dialect so the engine runs on the same psycopg3
    driver as the admin helper above — one driver, not two."""
    auth = PG_USER
    if PG_PASSWORD:
        auth += f":{PG_PASSWORD}"
    return f"postgresql+psycopg://{auth}@{PG_HOST}:{PG_PORT}/{dbname or PG_DB}"


def _create_database_if_missing(dbname: str) -> None:
    with psycopg.connect(dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))


class Base(DeclarativeBase):
    """Declarative base every ORM model (see models.py) inherits from."""


# Engine + session factory for the configured PG_DB. `pool_pre_ping` checks a
# pooled connection is still alive before handing it out, so a connection the
# server dropped (idle timeout, restart) doesn't surface as a confusing error
# on the next otherwise-unrelated query.
engine = create_engine(database_url(), echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Opens a session, yields it, and always closes it afterward — for
    callers that want dependency-injection-style usage:
    `with contextlib.ExitStack() as stack: session = stack.enter_context(get_session())`.
    models.py itself just uses `with SessionLocal() as session:` directly.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_engine(dbname: str):
    """Builds a standalone engine bound to `dbname`, separate from the
    module's default `engine`/`SessionLocal` — used by the test suite to
    point at a throwaway database without touching the real one."""
    return create_engine(database_url(dbname), pool_pre_ping=True)


def init_db(dbname: str | None = None) -> None:
    """Creates the target database if it doesn't exist yet, then creates
    every table declared on `Base` (see models.py's User/Category/Transaction/
    Budget) if it doesn't exist yet. Safe to call on every startup — table
    creation is idempotent."""
    _create_database_if_missing(dbname or PG_DB)
    bind = engine if dbname is None else make_engine(dbname)
    Base.metadata.create_all(bind=bind)


def drop_all_tables(dbname: str | None = None) -> None:
    """Drops every table declared on `Base`. Used by seed.py to reset the
    database the same way the old SQLite path did by deleting the file."""
    bind = engine if dbname is None else make_engine(dbname)
    Base.metadata.drop_all(bind=bind)


if __name__ == "__main__":
    import models  # noqa: F401 — registers User/Category/Transaction/Budget on Base.metadata

    init_db()
    print(f"Database initialized: {database_url()}")
