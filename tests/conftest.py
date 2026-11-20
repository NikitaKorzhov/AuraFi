from __future__ import annotations

import uuid as uuid_lib
from contextlib import contextmanager

import psycopg
import pytest
from psycopg import sql

import database
import models


@pytest.fixture
def temp_db(monkeypatch):
    """Creates a brand-new PostgreSQL database (random name, on the same
    server as PG_HOST/PG_PORT), initializes its schema, and redirects every
    models.py function to use it instead of the real PG_DB — by
    monkeypatching the `db_connection` name models.py calls.

    The database is dropped again after the test, so there is nothing to
    roll back manually and the real database is never touched.
    """
    dbname = f"aurafi_test_{uuid_lib.uuid4().hex[:16]}"

    with psycopg.connect(database.dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))

    database.init_db(dbname=dbname)

    @contextmanager
    def _db_connection(name: str = dbname):
        with database.db_connection(name) as conn:
            yield conn

    monkeypatch.setattr(models, "db_connection", _db_connection)

    yield dbname

    with psycopg.connect(database.dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname))
            )
