import logging

import pytest

import models
from decorators import currency_aware, log_transaction, validate_amount
from expense_tracker import Expense, ExpenseTracker, Income


# ---------------------------------------------------------------------------
# validate_amount — wraps Transaction.__init__ (shared by Income/Expense)
# ---------------------------------------------------------------------------

class TestValidateAmount:
    def test_positive_amount_constructs_normally(self):
        income = Income(100, "salary")
        assert income.amount == 100

    def test_zero_amount_is_rejected(self, caplog):
        with caplog.at_level(logging.WARNING, logger="decorators"):
            with pytest.raises(ValueError):
                Expense(0, "food")
        assert any("validate_amount" in r.message for r in caplog.records)

    def test_negative_amount_is_rejected(self):
        with pytest.raises(ValueError):
            Expense(-50, "food")

    def test_non_numeric_amount_is_rejected(self):
        with pytest.raises(ValueError):
            Income("not a number", "salary")

    def test_bool_amount_is_rejected(self):
        """bool is a subclass of int in Python — must not slip through as a valid amount."""
        with pytest.raises(ValueError):
            Income(True, "salary")

    def test_standalone_decorator_returns_wrapped_result_when_valid(self):
        @validate_amount
        def make(amount, label):
            return amount, label

        assert make(10, "ok") == (10, "ok")

    def test_standalone_decorator_raises_when_invalid(self):
        @validate_amount
        def make(amount, label):
            return amount, label

        with pytest.raises(ValueError):
            make(-1, "bad")


# ---------------------------------------------------------------------------
# log_transaction — wraps ExpenseTracker.add_transaction/remove_transaction
# and BudgetManager.set_budget
# ---------------------------------------------------------------------------

class TestLogTransaction:
    def test_add_transaction_is_logged(self, temp_db, caplog):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        with caplog.at_level(logging.INFO, logger="decorators"):
            tracker.add_transaction(Income(500, "salary"))

        assert any("add_transaction" in r.message for r in caplog.records)

    def test_remove_transaction_is_logged(self, temp_db, caplog):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(500, "salary"))

        with caplog.at_level(logging.INFO, logger="decorators"):
            tracker.remove_transaction(1)

        assert any("remove_transaction" in r.message for r in caplog.records)

    def test_set_budget_is_logged(self, temp_db, caplog):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        with caplog.at_level(logging.INFO, logger="decorators"):
            tracker.set_budget("food", "expense", 1000)

        assert any("set_budget" in r.message for r in caplog.records)

    def test_standalone_decorator_preserves_return_value_and_name(self):
        @log_transaction
        def add(a, b):
            return a + b

        assert add.__name__ == "add"
        assert add(2, 3) == 5


# ---------------------------------------------------------------------------
# currency_aware — stub, must not change behavior
# ---------------------------------------------------------------------------

class TestCurrencyAware:
    def test_passes_call_through_unchanged(self):
        @currency_aware()
        def make(amount):
            return amount * 2

        assert make(5) == 10

    def test_logs_debug_note_with_base_currency(self, caplog):
        @currency_aware(base_currency="EUR")
        def noop():
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="decorators"):
            noop()

        assert any("EUR" in r.message for r in caplog.records)

    def test_does_not_block_a_real_add_transaction(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        tracker.add_transaction(Income(500, "salary"))

        assert len(tracker.transactions) == 1
