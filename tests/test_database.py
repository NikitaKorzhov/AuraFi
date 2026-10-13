import sqlite3

import pytest

import database


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_all_three_tables(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.close()
        assert {"users", "transactions", "budgets"}.issubset(tables)

    def test_users_table_has_expected_columns(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        conn = sqlite3.connect(db_path)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        conn.close()
        assert columns == {"id", "username", "email", "password_hash"}

    def test_calling_init_db_twice_is_idempotent(self, tmp_path):
        """Boundary: re-running init_db() against an already-initialized file
        (e.g. main.py calling it on every startup) must not error or wipe data."""
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES ('a', 'a@x.com', 'h')"
        )
        conn.commit()
        conn.close()

        database.init_db(db_path=db_path)  # must not raise or clear the table

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        assert count == 1

    def test_missing_parent_directory_raises_sqlite_error(self, tmp_path):
        bad_path = str(tmp_path / "does_not_exist" / "x.db")
        with pytest.raises(sqlite3.Error):
            database.init_db(db_path=bad_path)

    def test_missing_init_sql_file_raises(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        with pytest.raises(FileNotFoundError):
            database.init_db(db_path=db_path, sql_path=str(tmp_path / "no_such.sql"))


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------

class TestGetConnection:
    def test_returns_a_working_connection(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        conn = database.get_connection(db_path)
        try:
            assert conn.execute("SELECT 1").fetchone() == (1,)
        finally:
            conn.close()

    def test_enables_foreign_key_enforcement(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        conn = database.get_connection(db_path)
        try:
            assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
        finally:
            conn.close()

    def test_foreign_key_violation_is_rejected(self, tmp_path):
        """With PRAGMA foreign_keys=ON, a transaction referencing a non-existent
        user_id must be rejected rather than silently stored as orphaned data."""
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        conn = database.get_connection(db_path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO transactions
                        (amount, transaction_type, category, date, description, user_id)
                    VALUES (10, 'expense', 'food', '2026-01-01', '', 9999)
                    """
                )
        finally:
            conn.close()

    def test_bad_path_logs_and_raises(self, tmp_path, caplog):
        import logging

        bad_path = str(tmp_path / "missing_dir" / "x.db")
        with caplog.at_level(logging.ERROR, logger="database"):
            with pytest.raises(sqlite3.Error):
                database.get_connection(bad_path)
        assert any("Failed to connect" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# db_connection (context manager)
# ---------------------------------------------------------------------------

class TestDbConnection:
    def test_closes_connection_on_success(self, tmp_path):
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        with database.db_connection(db_path) as conn:
            pass

        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_closes_connection_even_when_body_raises(self, tmp_path):
        """The connection must not leak (stay open) if the caller's code inside
        the `with` block throws — e.g. a bad query."""
        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        held_conn = None
        with pytest.raises(sqlite3.OperationalError):
            with database.db_connection(db_path) as conn:
                held_conn = conn
                conn.execute("SELECT * FROM no_such_table")

        with pytest.raises(sqlite3.ProgrammingError):
            held_conn.execute("SELECT 1")

    def test_query_error_is_logged(self, tmp_path, caplog):
        import logging

        db_path = str(tmp_path / "x.db")
        database.init_db(db_path=db_path)

        with caplog.at_level(logging.ERROR, logger="database"):
            with pytest.raises(sqlite3.OperationalError):
                with database.db_connection(db_path) as conn:
                    conn.execute("SELECT * FROM no_such_table")
        assert any("Database error" in r.message for r in caplog.records)
