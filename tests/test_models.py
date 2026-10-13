import sqlite3

import pytest

import models


def _raw_insert_transaction(db_path, user_id, amount, transaction_type, category, date):
    """Bypasses models.add_transaction's category normalization, to simulate
    legacy/mixed-case rows already sitting in the database."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO transactions (amount, transaction_type, category, date, description, user_id)
        VALUES (?, ?, ?, ?, '', ?)
        """,
        (amount, transaction_type, category, date, user_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# create_user / authenticate_user / get_username_by_email
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_returns_an_integer_id(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        assert isinstance(user_id, int)

    def test_duplicate_email_is_rejected(self, temp_db):
        """The `users.email` UNIQUE constraint must actually be enforced."""
        models.create_user("alice", "alice@example.com", "pw")
        with pytest.raises(sqlite3.IntegrityError):
            models.create_user("alice2", "alice@example.com", "other_pw")

    def test_password_is_not_stored_in_plaintext(self, temp_db):
        models.create_user("alice", "alice@example.com", "supersecret")
        conn = sqlite3.connect(temp_db)
        stored = conn.execute(
            "SELECT password_hash FROM users WHERE email = 'alice@example.com'"
        ).fetchone()[0]
        conn.close()
        assert "supersecret" not in stored


class TestAuthenticateUser:
    def test_correct_credentials_return_user_id(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw123")
        assert models.authenticate_user("alice@example.com", "pw123") == user_id

    def test_wrong_password_returns_none(self, temp_db):
        models.create_user("alice", "alice@example.com", "pw123")
        assert models.authenticate_user("alice@example.com", "WRONG") is None

    def test_unknown_email_returns_none(self, temp_db):
        assert models.authenticate_user("nobody@example.com", "pw123") is None

    def test_empty_password_is_rejected_not_crashed(self, temp_db):
        models.create_user("alice", "alice@example.com", "pw123")
        assert models.authenticate_user("alice@example.com", "") is None

    def test_email_match_is_case_sensitive(self, temp_db):
        """Documents current behavior: email lookup is an exact '=' match, so a
        differently-cased email is treated as unknown rather than matched."""
        models.create_user("alice", "alice@example.com", "pw123")
        assert models.authenticate_user("ALICE@example.com", "pw123") is None


class TestGetUsernameByEmail:
    def test_returns_username_for_known_email(self, temp_db):
        models.create_user("alice", "alice@example.com", "pw123")
        assert models.get_username_by_email("alice@example.com") == "alice"

    def test_returns_none_for_unknown_email(self, temp_db):
        assert models.get_username_by_email("nobody@example.com") is None


# ---------------------------------------------------------------------------
# add_transaction
# ---------------------------------------------------------------------------

class TestAddTransaction:
    def test_invalid_transaction_type_raises_value_error(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        with pytest.raises(ValueError):
            models.add_transaction(user_id, 10, "transfer", "food", "")

    def test_category_is_normalized_to_lowercase_and_stripped(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tx_id = models.add_transaction(user_id, 10, "expense", "  FOOD  ", "")
        conn = sqlite3.connect(temp_db)
        stored = conn.execute(
            "SELECT category FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()[0]
        conn.close()
        assert stored == "food"

    def test_date_defaults_to_today_when_not_given(self, temp_db):
        from datetime import date

        user_id = models.create_user("alice", "alice@example.com", "pw")
        tx_id = models.add_transaction(user_id, 10, "expense", "food", "")
        conn = sqlite3.connect(temp_db)
        stored = conn.execute(
            "SELECT date FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()[0]
        conn.close()
        assert stored == date.today().isoformat()

    def test_explicit_date_is_preserved(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tx_id = models.add_transaction(user_id, 10, "expense", "food", "", date="2020-01-01")
        conn = sqlite3.connect(temp_db)
        stored = conn.execute(
            "SELECT date FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()[0]
        conn.close()
        assert stored == "2020-01-01"


# ---------------------------------------------------------------------------
# get_all_transactions
# ---------------------------------------------------------------------------

class TestGetAllTransactions:
    def test_empty_for_a_brand_new_user(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        assert models.get_all_transactions(user_id) == []

    def test_ordered_by_date_then_id(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        third = models.add_transaction(user_id, 1, "expense", "food", "", date="2026-01-03")
        first = models.add_transaction(user_id, 1, "expense", "food", "", date="2026-01-01")
        second = models.add_transaction(user_id, 1, "expense", "food", "", date="2026-01-02")

        ids = [tx["id"] for tx in models.get_all_transactions(user_id)]
        assert ids == [first, second, third]

    def test_only_returns_the_given_users_transactions(self, temp_db):
        """Isolation boundary: one user must never see another user's rows."""
        user_a = models.create_user("alice", "alice@example.com", "pw")
        user_b = models.create_user("bob", "bob@example.com", "pw")
        models.add_transaction(user_a, 10, "expense", "food", "")
        models.add_transaction(user_b, 20, "expense", "food", "")

        assert len(models.get_all_transactions(user_a)) == 1
        assert len(models.get_all_transactions(user_b)) == 1


# ---------------------------------------------------------------------------
# get_balance
# ---------------------------------------------------------------------------

class TestGetBalance:
    def test_zero_for_a_user_with_no_transactions(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        assert models.get_balance(user_id) == 0.0

    def test_income_minus_expenses(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 500, "income", "salary", "")
        models.add_transaction(user_id, 120, "expense", "food", "")
        assert models.get_balance(user_id) == 380.0

    def test_can_go_negative(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 200, "expense", "rent", "")
        assert models.get_balance(user_id) == -200.0


# ---------------------------------------------------------------------------
# get_expenses_by_category
# ---------------------------------------------------------------------------

class TestGetExpensesByCategory:
    def test_empty_when_no_expenses(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 500, "income", "salary", "")
        assert models.get_expenses_by_category(user_id) == []

    def test_income_is_excluded(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        models.add_transaction(user_id, 500, "income", "food", "")
        models.add_transaction(user_id, 50, "expense", "food", "")
        rows = models.get_expenses_by_category(user_id)
        assert rows == [{"category": "food", "total": 50}]

    def test_mixed_case_categories_are_merged(self, temp_db):
        """Regression guard: 'Food' and 'food' must be summed as one category,
        even for rows written before normalization (direct SQL insert here
        simulates that legacy state)."""
        user_id = models.create_user("alice", "alice@example.com", "pw")
        _raw_insert_transaction(temp_db, user_id, 100, "expense", "Food", "2026-01-01")
        _raw_insert_transaction(temp_db, user_id, 50, "expense", "food", "2026-01-02")

        rows = models.get_expenses_by_category(user_id)
        assert rows == [{"category": "food", "total": 150}]


# ---------------------------------------------------------------------------
# set_budget
# ---------------------------------------------------------------------------

class TestSetBudget:
    def test_creates_a_new_budget_and_returns_its_id(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        budget_id = models.set_budget(user_id, "food", "expense", 1000)
        assert isinstance(budget_id, int)

    def test_second_call_updates_limit_instead_of_duplicating(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        first_id = models.set_budget(user_id, "food", "expense", 1000)
        second_id = models.set_budget(user_id, "food", "expense", 2000)
        assert first_id == second_id

        conn = sqlite3.connect(temp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM budgets WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        conn.close()
        assert count == 1

    def test_different_case_matches_the_same_existing_budget(self, temp_db):
        """Regression guard for the 'Food' vs 'food' duplicate-budget-row bug:
        setting a budget with different casing must update the existing row."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "Food", "expense", 1000)
        models.set_budget(user_id, "food", "expense", 2000)

        conn = sqlite3.connect(temp_db)
        rows = conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id = ?", (user_id,)
        ).fetchall()
        conn.close()
        assert rows == [("food", 2000)]

    def test_rejects_invalid_transaction_type(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        with pytest.raises(ValueError):
            models.set_budget(user_id, "food", "transfer", 1000)

    def test_income_category_can_have_no_limit(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "salary", "income", None)
        assert models.get_categories(user_id, "income") == {"salary": None}


# ---------------------------------------------------------------------------
# get_categories
# ---------------------------------------------------------------------------

class TestGetCategories:
    def test_new_user_gets_the_default_expense_categories(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        assert models.get_categories(user_id, "expense") == models.DEFAULT_EXPENSE_CATEGORIES

    def test_new_user_gets_the_default_income_categories_with_no_limit(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        income = models.get_categories(user_id, "income")
        assert set(income) == set(models.DEFAULT_INCOME_CATEGORIES)
        assert all(limit is None for limit in income.values())

    def test_seed_default_categories_false_gives_a_blank_slate(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        assert models.get_categories(user_id, "expense") == {}
        assert models.get_categories(user_id, "income") == {}

    def test_only_returns_the_given_users_categories(self, temp_db):
        user_a = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        user_b = models.create_user("bob", "bob@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_a, "food", "expense", 1000)
        models.set_budget(user_b, "rent", "expense", 2000)

        assert models.get_categories(user_a, "expense") == {"food": 1000}


# ---------------------------------------------------------------------------
# get_budget_limits
# ---------------------------------------------------------------------------

class TestGetBudgetLimits:
    def test_budget_with_no_spending_shows_zero(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 1000)
        assert models.get_budget_limits(user_id) == [
            {"category": "food", "monthly_limit": 1000, "spent": 0}
        ]

    def test_spending_is_summed_against_the_limit(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 1000)
        models.add_transaction(user_id, 100, "expense", "food", "")
        models.add_transaction(user_id, 50, "expense", "food", "")
        rows = models.get_budget_limits(user_id)
        assert rows == [{"category": "food", "monthly_limit": 1000, "spent": 150}]

    def test_mixed_case_legacy_transactions_do_not_get_double_counted(self, temp_db):
        """Regression guard: this is the exact scenario that caused real double
        counting before the LOWER()-based JOIN fix — a legacy mixed-case
        transaction row must be counted exactly once, not once per differently
        cased budget match."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 1000)
        _raw_insert_transaction(temp_db, user_id, 100, "expense", "FOOD", "2026-01-01")

        rows = models.get_budget_limits(user_id)
        assert rows == [{"category": "food", "monthly_limit": 1000, "spent": 100}]

    def test_only_includes_the_given_users_budgets(self, temp_db):
        user_a = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        user_b = models.create_user("bob", "bob@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_a, "food", "expense", 1000)
        models.set_budget(user_b, "rent", "expense", 2000)

        assert [r["category"] for r in models.get_budget_limits(user_a)] == ["food"]

    def test_income_categories_are_excluded(self, temp_db):
        """Regression guard: budgets now also holds income categories (with a
        NULL limit) — get_budget_limits must filter to expense only, or a None
        limit would break the '>' comparison callers do against it."""
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "salary", "income", None)
        models.set_budget(user_id, "food", "expense", 1000)

        assert [r["category"] for r in models.get_budget_limits(user_id)] == ["food"]


# ---------------------------------------------------------------------------
# delete_transaction
# ---------------------------------------------------------------------------

class TestDeleteTransaction:
    def test_returns_true_when_a_row_is_removed(self, temp_db):
        user_id = models.create_user("alice", "alice@example.com", "pw")
        tx_id = models.add_transaction(user_id, 10, "expense", "food", "")
        assert models.delete_transaction(tx_id) is True
        assert models.get_all_transactions(user_id) == []

    def test_returns_false_for_a_nonexistent_id(self, temp_db):
        models.create_user("alice", "alice@example.com", "pw")
        assert models.delete_transaction(999999) is False


# ---------------------------------------------------------------------------
# check_budget_status
# ---------------------------------------------------------------------------

class TestCheckBudgetStatus:
    def test_only_counts_the_current_month(self, temp_db):
        """Boundary: an expense from a past month must not count toward this
        month's spend, even though get_budget_limits (all-time) would include it."""
        from datetime import date

        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.add_transaction(user_id, 5000, "expense", "food", "", date="2020-01-01")

        statuses = models.check_budget_status(user_id)
        assert statuses == [
            {"category": "food", "monthly_limit": 100, "spent": 0, "exceeded": False}
        ]

    def test_exceeded_flag_is_true_when_over_limit(self, temp_db):
        from datetime import date

        today = date.today().isoformat()
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.add_transaction(user_id, 150, "expense", "food", "", date=today)

        statuses = models.check_budget_status(user_id)
        assert statuses[0]["exceeded"] is True

    def test_prints_a_warning_only_when_exceeded(self, temp_db, capsys):
        from datetime import date

        today = date.today().isoformat()
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.set_budget(user_id, "rent", "expense", 100)
        models.add_transaction(user_id, 150, "expense", "food", "", date=today)
        models.add_transaction(user_id, 50, "expense", "rent", "", date=today)

        models.check_budget_status(user_id)
        out = capsys.readouterr().out
        assert "food" in out.lower()
        assert "rent" not in out.lower()

    def test_exactly_at_limit_is_not_exceeded(self, temp_db):
        """Boundary: spent == limit must not count as exceeded (strict '>')."""
        from datetime import date

        today = date.today().isoformat()
        user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
        models.set_budget(user_id, "food", "expense", 100)
        models.add_transaction(user_id, 100, "expense", "food", "", date=today)

        statuses = models.check_budget_status(user_id)
        assert statuses[0]["exceeded"] is False
