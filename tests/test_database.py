from __future__ import annotations

import uuid as uuid_lib

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

import database
import models  # noqa: F401 — registers User/Category/Transaction/Budget on Base.metadata


def _random_dbname() -> str:
    return f"aurafi_test_{uuid_lib.uuid4().hex[:16]}"


def _drop(dbname: str) -> None:
    with psycopg.connect(database.dsn("postgres"), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname)))


@pytest.fixture
def fresh_dbname():
    dbname = _random_dbname()
    yield dbname
    _drop(dbname)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_all_four_tables(self, fresh_dbname):
        database.init_db(dbname=fresh_dbname)

        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                ).fetchall()
            }
        assert {"users", "categories", "transactions", "budgets"}.issubset(tables)

    def test_users_table_has_expected_columns(self, fresh_dbname):
        database.init_db(dbname=fresh_dbname)

        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            columns = {
                row[0]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
                ).fetchall()
            }
        assert columns == {"id", "username", "email", "password_hash"}

    def test_calling_init_db_twice_is_idempotent(self, fresh_dbname):
        """Boundary: re-running init_db() against an already-initialized database
        (e.g. main.py calling it on every startup) must not error or wipe data."""
        database.init_db(dbname=fresh_dbname)

        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES ('a', 'a@x.com', 'h')"
            )
            conn.commit()

        database.init_db(dbname=fresh_dbname)  # must not raise or clear the table

        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 1

    def test_creates_the_database_when_it_does_not_exist_yet(self, fresh_dbname):
        with psycopg.connect(database.dsn("postgres")) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (fresh_dbname,)
            ).fetchone()
        assert exists is None

        database.init_db(dbname=fresh_dbname)

        with psycopg.connect(database.dsn("postgres")) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (fresh_dbname,)
            ).fetchone()
        assert exists is not None


# ---------------------------------------------------------------------------
# make_engine / SQLAlchemy session basics
# ---------------------------------------------------------------------------

class TestMakeEngine:
    def test_returns_a_working_session(self, fresh_dbname):
        database.init_db(dbname=fresh_dbname)
        engine = database.make_engine(fresh_dbname)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1

    def test_foreign_key_violation_is_rejected(self, fresh_dbname):
        """PostgreSQL enforces FOREIGN KEY constraints unconditionally, so a
        transaction referencing a non-existent user_id must be rejected
        rather than silently stored as orphaned data."""
        database.init_db(dbname=fresh_dbname)
        engine = database.make_engine(fresh_dbname)

        with engine.connect() as conn:
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        """
                        INSERT INTO transactions
                            (amount, transaction_type, category_uuid, date, description, user_id)
                        VALUES (10, 'expense', 'nonexistent-category-uuid', '2026-01-01', '', 9999)
                        """
                    )
                )
                conn.commit()

    def test_unknown_database_raises(self):
        bad_dbname = _random_dbname()  # never created
        engine = database.make_engine(bad_dbname)
        with pytest.raises(OperationalError):
            with engine.connect():
                pass


# ---------------------------------------------------------------------------
# drop_all_tables
# ---------------------------------------------------------------------------

class TestDropAllTables:
    def test_removes_all_rows_and_tables_can_be_recreated(self, fresh_dbname):
        database.init_db(dbname=fresh_dbname)
        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES ('a', 'a@x.com', 'h')"
            )
            conn.commit()

        database.drop_all_tables(fresh_dbname)
        database.init_db(dbname=fresh_dbname)

        with psycopg.connect(database.dsn(fresh_dbname)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 0
