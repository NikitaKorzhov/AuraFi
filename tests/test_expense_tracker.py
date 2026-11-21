import pytest

import models
from expense_tracker import Budget, Expense, ExpenseTracker, Income, User


# ---------------------------------------------------------------------------
# Transaction / Income / Expense (in-memory, kopecks conversion + arithmetic)
# ---------------------------------------------------------------------------

class TestTransactionArithmetic:
    def test_income_kopecks_conversion(self):
        income = Income(44.7, "food")
        assert income.amount_kopecks == 4470

    def test_expense_signed_amount_is_negative(self):
        expense = Expense(100, "food")
        assert expense.signed_amount == -10000

    def test_income_signed_amount_is_positive(self):
        income = Income(100, "salary")
        assert income.signed_amount == 10000

    def test_sum_builtin_works_via_radd(self):
        transactions = [Income(100, "salary"), Income(50, "gift"), Expense(30, "food")]
        assert sum(transactions) == 12000  # 10000 + 5000 - 3000 kopecks


# ---------------------------------------------------------------------------
# Budget.check_limit
# ---------------------------------------------------------------------------

class TestBudgetCheckLimit:
    def test_exactly_at_limit_is_not_exceeded(self):
        budget = Budget("food", "expense", 50)
        exceeded, spent = budget.check_limit([Expense(50, "food")])
        assert exceeded is False
        assert spent == 50

    def test_over_limit_is_exceeded(self):
        budget = Budget("food", "expense", 50)
        exceeded, spent = budget.check_limit([Expense(50.01, "food")])
        assert exceeded is True

    def test_none_limit_never_exceeds(self):
        """Income categories have monthly_limit=None — never flagged as exceeded,
        regardless of spend."""
        budget = Budget("salary", "income", None)
        exceeded, spent = budget.check_limit([Expense(1_000_000, "salary")])
        assert exceeded is False


# ---------------------------------------------------------------------------
# Transaction.is_expense / formatted (Homework 22, Частина 2)
# ---------------------------------------------------------------------------

class TestTransactionFormatting:
    def test_is_expense_true_for_expense(self):
        assert Expense(50, "food").is_expense() is True

    def test_is_expense_false_for_income(self):
        assert Income(50, "salary").is_expense() is False

    def test_formatted_income_has_plus_sign(self):
        tx = Income(5000, "salary", date="2024-03-15")
        assert tx.formatted() == "+ 5000.00 UAH [salary] 2024-03-15"

    def test_formatted_expense_has_minus_sign(self):
        tx = Expense(350, "food", date="2024-03-15")
        assert tx.formatted() == "- 350.00 UAH [food] 2024-03-15"


# ---------------------------------------------------------------------------
# Budget.remaining / is_exceeded / utilization_pct (Homework 22, Частина 2)
# ---------------------------------------------------------------------------

class TestBudgetNewMethods:
    def test_remaining_with_no_spending(self):
        budget = Budget("food", "expense", 100)
        assert budget.remaining([]) == 100

    def test_remaining_after_spending(self):
        budget = Budget("food", "expense", 100)
        assert budget.remaining([Expense(30, "food")]) == 70

    def test_remaining_can_go_negative(self):
        budget = Budget("food", "expense", 100)
        assert budget.remaining([Expense(150, "food")]) == -50

    def test_remaining_is_none_without_limit(self):
        budget = Budget("salary", "income", None)
        assert budget.remaining([Expense(1000, "salary")]) is None

    def test_is_exceeded_true_over_limit(self):
        budget = Budget("food", "expense", 50)
        assert budget.is_exceeded([Expense(50.01, "food")]) is True

    def test_is_exceeded_false_at_limit(self):
        """Boundary: spent == limit must not count as exceeded (strict '>')."""
        budget = Budget("food", "expense", 50)
        assert budget.is_exceeded([Expense(50, "food")]) is False

    def test_utilization_pct_half_spent(self):
        budget = Budget("food", "expense", 100)
        assert budget.utilization_pct([Expense(50, "food")]) == 50.0

    def test_utilization_pct_over_100_when_exceeded(self):
        budget = Budget("food", "expense", 100)
        assert budget.utilization_pct([Expense(150, "food")]) == 150.0

    def test_utilization_pct_zero_without_limit(self):
        budget = Budget("salary", "income", None)
        assert budget.utilization_pct([]) == 0.0


# ---------------------------------------------------------------------------
# User (Homework 22, Частина 2)
# ---------------------------------------------------------------------------

class TestUserDataclass:
    def test_display_format(self):
        user = User("nikita", "nikita@example.com")
        assert user.display() == "nikita <nikita@example.com>"

    def test_default_currency(self):
        assert User("a", "b@x.com").currency == "UAH"


# ---------------------------------------------------------------------------
# ExpenseTracker.spending_report (Homework 22, Частина 2 — filter/map/reduce/sorted)
# ---------------------------------------------------------------------------

class TestSpendingReport:
    def test_includes_income_and_expense_lines_and_totals(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(500, "salary", date="2024-01-01"))
        tracker.add_transaction(Expense(120, "food", date="2024-01-02"))

        report = tracker.spending_report()

        assert "+ 500.00 UAH [salary] 2024-01-01" in report
        assert "- 120.00 UAH [food] 2024-01-02" in report
        assert "Доходи:  +500.00 UAH" in report
        assert "Витрати: -120.00 UAH" in report
        assert "Баланс:   380.00 UAH" in report

    def test_sorted_by_amount_descending(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(30, "gift"))
        tracker.add_transaction(Income(900, "salary"))

        report = tracker.spending_report()
        assert report.index("900.00") < report.index("30.00")

    def test_empty_tracker_shows_placeholder(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        assert "empty" in tracker.spending_report().lower()

    def test_food_category_subsection_only_lists_food_expenses(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Expense(100, "food", date="2024-01-01"))
        tracker.add_transaction(Expense(40, "transport", date="2024-01-02"))

        report = tracker.spending_report()

        assert "Витрати [food]:" in report
        assert "- 100.00 UAH [food] 2024-01-01" in report
        food_section = report.split("Витрати [food]:")[1].split("\n\n")[0]
        assert "transport" not in food_section

    def test_no_food_subsection_when_no_food_expenses(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Expense(40, "transport"))

        assert "Витрати [food]" not in tracker.spending_report()


# ---------------------------------------------------------------------------
# ExpenseTracker — state changes must persist to the database
# ---------------------------------------------------------------------------

class TestExpenseTrackerPersistence:
    def test_add_transaction_persists_to_db(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        tracker.add_transaction(Income(500, "salary"))

        assert len(tracker.transactions) == 1
        db_rows = models.get_all_transactions(user_id)
        assert len(db_rows) == 1
        assert db_rows[0]["category"] == "salary"
        assert db_rows[0]["amount"] == 500

    def test_added_transaction_gets_a_real_db_id(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        transaction = Income(500, "salary")
        assert transaction.id is None
        tracker.add_transaction(transaction)
        assert transaction.id is not None

    def test_remove_transaction_persists_deletion_to_db(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(500, "salary"))

        tracker.remove_transaction(1)

        assert tracker.transactions == []
        assert models.get_all_transactions(user_id) == []

    def test_from_db_rebuilds_existing_transactions(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.add_transaction(user_id, 500, "income", "salary", "")
        models.add_transaction(user_id, 30, "expense", "food", "")

        tracker = ExpenseTracker.from_db(user_id)

        assert len(tracker.transactions) == 2
        assert isinstance(tracker.transactions[0], (Income, Expense))

    def test_rejected_expense_is_not_persisted(self, temp_db):
        """A budget-exceeding expense must not reach the database at all."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.set_budget("food", "expense", 50)

        with pytest.raises(ValueError):
            tracker.add_transaction(Expense(100, "food"))

        assert tracker.transactions == []
        assert models.get_all_transactions(user_id) == []

    def test_set_budget_persists_to_db(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)

        tracker.set_budget("food", "expense", 1000)

        assert models.get_categories(user_id, "expense") == {"food": 1000}

    def test_budget_manager_is_reloaded_fresh_by_from_db(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "rent", "expense", 2000)

        tracker = ExpenseTracker.from_db(user_id)

        assert tracker.get_categories("expense") == {"rent": 2000}

    def test_calc_balance_reflects_in_memory_state_after_mutation(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(500, "salary"))
        tracker.add_transaction(Expense(120, "food"))

        assert tracker.calc_balance() == 380
        assert tracker.calc_income() == 500
        assert tracker.calc_expense() == 120

    def test_str_on_empty_tracker(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        assert "empty" in str(tracker).lower()

    def test_remove_transaction_out_of_range_raises_without_db_call(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        tracker = ExpenseTracker.from_db(user_id)
        tracker.add_transaction(Income(500, "salary"))

        with pytest.raises(IndexError):
            tracker.remove_transaction(99)

        assert len(tracker.transactions) == 1
        assert len(models.get_all_transactions(user_id)) == 1
