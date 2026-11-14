import logging

import pytest

import main
import models
from expense_tracker import ExpenseTracker


def feed_input(monkeypatch, values):
    """Feeds canned responses to builtins.input(), one per call, in order."""
    it = iter(values)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_cancel_at_email_prompt_returns_none(self, temp_db, monkeypatch):
        feed_input(monkeypatch, ["q"])
        assert main.login() is None

    def test_correct_credentials_return_user_id(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw123")
        feed_input(monkeypatch, ["alice@example.com"])
        monkeypatch.setattr(main.getpass, "getpass", lambda prompt="": "pw123")

        assert main.login() == user_id

    def test_wrong_password_then_correct_password_eventually_succeeds(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw123")
        feed_input(monkeypatch, ["alice@example.com", "alice@example.com"])
        passwords = iter(["WRONG", "pw123"])
        monkeypatch.setattr(main.getpass, "getpass", lambda prompt="": next(passwords))

        assert main.login() == user_id

    def test_unknown_email_fails_gracefully_not_crashes(self, temp_db, monkeypatch, caplog):
        feed_input(monkeypatch, ["nobody@example.com", "q"])
        monkeypatch.setattr(main.getpass, "getpass", lambda prompt="": "whatever")

        with caplog.at_level(logging.ERROR, logger="main"):
            result = main.login()

        assert result is None
        assert any("unknown email" in r.message.lower() for r in caplog.records)

    def test_successful_login_is_logged_with_username(self, temp_db, monkeypatch, caplog):
        models.create_user("alice", "alice@example.com", "pw123")
        feed_input(monkeypatch, ["alice@example.com"])
        monkeypatch.setattr(main.getpass, "getpass", lambda prompt="": "pw123")

        with caplog.at_level(logging.INFO, logger="main"):
            main.login()

        assert any(
            "logged in successfully" in r.message and "alice" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# add_transaction_entry — budget enforcement
# ---------------------------------------------------------------------------

class TestAddTransactionEntry:
    def test_does_nothing_when_input_is_canceled(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(main, "input_transaction", lambda t, c=None: None)

        main.add_transaction_entry(tracker, "expense")

        assert tracker.transactions == []

    def test_expense_within_budget_is_added(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(
            main, "input_transaction", lambda t, c=None: {"amount": 50, "category": "food"}
        )

        main.add_transaction_entry(tracker, "expense")

        assert len(tracker.transactions) == 1
        assert models.get_all_transactions(user_id)[0]["category"] == "food"

    def test_expense_exactly_at_limit_is_allowed(self, temp_db, monkeypatch):
        """Boundary: strict '>' comparison means landing exactly on the limit
        must succeed, matching the old expense_tracker.BudgetManager behavior."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(
            main, "input_transaction", lambda t, c=None: {"amount": 100, "category": "food"}
        )

        main.add_transaction_entry(tracker, "expense")

        assert len(tracker.transactions) == 1

    def test_expense_over_limit_is_rejected_and_not_persisted(self, temp_db, monkeypatch, caplog):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(
            main, "input_transaction", lambda t, c=None: {"amount": 101, "category": "food"}
        )

        with caplog.at_level(logging.ERROR, logger="main"):
            main.add_transaction_entry(tracker, "expense")

        assert tracker.transactions == []
        assert models.get_all_transactions(user_id) == []
        assert any("limit exceeded" in r.message.lower() for r in caplog.records)

    def test_category_with_no_budget_set_never_rejects(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(
            main, "input_transaction", lambda t, c=None: {"amount": 1_000_000, "category": "food"}
        )

        main.add_transaction_entry(tracker, "expense")

        assert len(tracker.transactions) == 1

    def test_category_menu_is_sourced_from_the_database(self, temp_db, monkeypatch):
        """The single-source-of-truth check: add_transaction_entry must build the
        category menu from whatever is actually in the user's budgets table, not
        from a hardcoded Python list."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "custom_category", "expense", 42)
        tracker = ExpenseTracker.from_db(user_id)

        seen_categories = {}

        def fake_input_transaction(t, categories=None):
            seen_categories.update(categories or {})
            return None

        monkeypatch.setattr(main, "input_transaction", fake_input_transaction)

        main.add_transaction_entry(tracker, "expense")

        assert seen_categories == {"custom_category": 42}

    def test_income_is_never_checked_against_a_budget(self, temp_db, monkeypatch):
        """Even though 'salary' exists as an income category (default-seeded,
        limit always None), amounts are never checked against any limit for
        income transactions — add_transaction only validates expenses."""
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(
            main, "input_transaction", lambda t, c=None: {"amount": 1_000_000, "category": "salary"}
        )

        main.add_transaction_entry(tracker, "income")

        assert len(tracker.transactions) == 1


# ---------------------------------------------------------------------------
# delete_transaction_entry
# ---------------------------------------------------------------------------

class TestDeleteTransactionEntry:
    def test_empty_list_shows_message_and_does_not_crash(self, temp_db, capsys):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tracker = ExpenseTracker.from_db(user_id)
        main.delete_transaction_entry(tracker)
        assert "no transactions to delete" in capsys.readouterr().out.lower()

    def test_valid_index_deletes_and_persists(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 10, "expense", "food", "")
        models.add_transaction(user_id, 20, "expense", "rent", "")
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(main, "input_index_to_delete", lambda *a, **k: 1)

        main.delete_transaction_entry(tracker)

        assert len(tracker.transactions) == 1
        assert tracker.transactions[0].category == "rent"
        remaining = models.get_all_transactions(user_id)
        assert len(remaining) == 1
        assert remaining[0]["category"] == "rent"

    def test_out_of_range_index_deletes_nothing(self, temp_db, monkeypatch, caplog):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 10, "expense", "food", "")
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(main, "input_index_to_delete", lambda *a, **k: 99)

        with caplog.at_level(logging.ERROR, logger="main"):
            main.delete_transaction_entry(tracker)

        assert len(tracker.transactions) == 1
        assert len(models.get_all_transactions(user_id)) == 1
        assert any("out of range" in r.message.lower() for r in caplog.records)

    def test_cancel_during_prompt_deletes_nothing(self, temp_db, monkeypatch):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 10, "expense", "food", "")
        tracker = ExpenseTracker.from_db(user_id)
        monkeypatch.setattr(main, "input_index_to_delete", lambda *a, **k: None)

        main.delete_transaction_entry(tracker)

        assert len(tracker.transactions) == 1


# ---------------------------------------------------------------------------
# show_all_transactions / show_all_transactions_with_info
# ---------------------------------------------------------------------------

class TestShowAllTransactions:
    def test_empty_shows_no_transactions_message(self, temp_db, capsys):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tracker = ExpenseTracker.from_db(user_id)
        main.show_all_transactions(tracker)
        assert "no transactions found" in capsys.readouterr().out.lower()

    def test_non_empty_lists_the_category(self, temp_db, capsys):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 10, "expense", "food", "")
        tracker = ExpenseTracker.from_db(user_id)
        main.show_all_transactions(tracker)
        assert "food" in capsys.readouterr().out.lower()

    def test_with_info_includes_balance_and_budget_line(self, temp_db, capsys):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.add_transaction(user_id, 30, "expense", "food", "")
        tracker = ExpenseTracker.from_db(user_id)

        main.show_all_transactions_with_info(tracker)

        out = capsys.readouterr().out
        assert "food" in out.lower()
        assert "100" in out
