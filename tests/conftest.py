from __future__ import annotations

import uuid as uuid_lib

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.orm import sessionmaker

import database
import models


@pytest.fixture
def temp_db(monkeypatch):
    """Creates a brand-new PostgreSQL database (random name, on the same
    server as PG_HOST/PG_PORT), creates its tables from the ORM models, and
    redirects every models.py function to use it instead of the real PG_DB —
    by monkeypatching the `SessionLocal` name models.py calls.

    The database is dropped again after the test, so there is nothing to
    roll back manually and the real database is never touched.
    """
    dbname = f"aurafi_test_{uuid_lib.uuid4().hex[:16]}"

    with psycopg.connect(database.dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))

    test_engine = database.make_engine(dbname)
    database.Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(models, "SessionLocal", test_session_factory)

    yield dbname

    test_engine.dispose()
    with psycopg.connect(database.dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname))
            )
