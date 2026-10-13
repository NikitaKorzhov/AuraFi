from __future__ import annotations

from contextlib import contextmanager

import pytest

import database
import models


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Creates a brand-new SQLite database under pytest's tmp_path, initializes
    its schema, and redirects every models.py function to use it instead of the
    real aurafi.db — by monkeypatching the `db_connection` name models.py calls.

    tmp_path is wiped by pytest after the test on its own, so there is nothing
    to roll back manually and the real database is never touched.
    """
    db_path = str(tmp_path / "test_aurafi.db")
    database.init_db(db_path=db_path)

    @contextmanager
    def _db_connection(path: str = db_path):
        with database.db_connection(path) as conn:
            yield conn

    monkeypatch.setattr(models, "db_connection", _db_connection)
    return db_path
