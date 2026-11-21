"""Homework 36, Task 10 (bonus): the same ORM models/functions from the live
app, run against an in-memory SQLite engine instead of PostgreSQL — proving
the Homework 36 migration in models.py is genuinely engine-portable, not
Postgres-specific code wearing an ORM costume. In particular, the LIKE-based
current-month filter in check_budget_status (not Postgres' SUBSTRING) and the
engine-generic Text/Float column types only matter because of this file.

Run directly: pytest orm_homework/test_models_sqlite.py -v
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import database
import models


@pytest.fixture
def sqlite_session(monkeypatch):
    """Points models.py's SessionLocal at a fresh in-memory SQLite database
    instead of the real PostgreSQL one, for the duration of one test."""
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(models, "SessionLocal", session_factory)
    yield
    engine.dispose()


class TestUserCrudOnSqlite:
    def test_create_and_look_up_by_email(self, sqlite_session):
        user_id = models.create_user("sqlite_alice", "alice@sqlite.test", "pw", seed_default_categories=False)
        assert isinstance(user_id, int)
        assert models.get_username_by_email("alice@sqlite.test") == "sqlite_alice"

    def test_authenticate_user(self, sqlite_session):
        models.create_user("sqlite_bob", "bob@sqlite.test", "pw", seed_default_categories=False)
        assert models.authenticate_user("bob@sqlite.test", "pw") is not None
        assert models.authenticate_user("bob@sqlite.test", "WRONG") is None

    def test_duplicate_email_is_rejected(self, sqlite_session):
        models.create_user("sqlite_charlie", "charlie@sqlite.test", "pw", seed_default_categories=False)
        with pytest.raises(IntegrityError):
            models.create_user("sqlite_charlie2", "charlie@sqlite.test", "pw", seed_default_categories=False)


class TestBudgetFlowOnSqlite:
    def test_full_transaction_and_budget_flow(self, sqlite_session):
        user_id = models.create_user("sqlite_dana", "dana@sqlite.test", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 1000)
        models.add_transaction(user_id, 100, "expense", "food", "", date="2026-01-01")
        models.add_transaction(user_id, 50, "expense", "food", "", date="2026-01-02")

        assert models.get_budget_limits(user_id) == [
            {"category": "food", "monthly_limit": 1000, "spent": 150}
        ]

    def test_check_budget_status_month_filter_is_portable(self, sqlite_session):
        """Regression guard: this relies on the LIKE-based month filter in
        check_budget_status, not Postgres' SUBSTRING — must pass here too."""
        today = date.today().isoformat()
        user_id = models.create_user("sqlite_erin", "erin@sqlite.test", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.add_transaction(user_id, 5000, "expense", "food", "", date="2020-01-01")
        models.add_transaction(user_id, 50, "expense", "food", "", date=today)

        statuses = models.check_budget_status(user_id)
        assert statuses == [{"category": "food", "monthly_limit": 100, "spent": 50, "exceeded": False}]
