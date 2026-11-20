from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import psycopg

from logger import get_logger
from postgres.config import dsn

log = get_logger(__name__)


@contextmanager
def get_db_connection(dbname: str | None = None) -> Generator[psycopg.Connection, None, None]:
    """Opens a connection, yields it, and always closes it afterward.

    Any `psycopg.Error` raised while the connection is in use is logged here
    before being re-raised, so every script below gets that handling for
    free just by using this (or `get_db_cursor`) instead of `psycopg.connect`
    directly — one place owns connection lifecycle and error logging.
    """
    conn = psycopg.connect(dsn(dbname))
    try:
        yield conn
    except psycopg.Error as e:
        log.error(f"PostgreSQL error on {dbname or 'default'} db: {e}")
        raise
    finally:
        conn.close()


@contextmanager
def get_db_cursor(dbname: str | None = None) -> Generator[psycopg.Cursor, None, None]:
    """Same lifecycle as `get_db_connection`, but hands back a cursor and
    commits on a clean exit. If the body raises, the connection is closed
    without a commit, which rolls back whatever was pending."""
    with get_db_connection(dbname) as conn:
        with conn.cursor() as cur:
            yield cur
            conn.commit()
