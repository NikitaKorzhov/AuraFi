import pytest
import expense_tracker as tracker


@pytest.fixture
def empty_tracker():
    return tracker.ExpenseTracker()


# ---------------------------------------------------------------------------
# add_transaction
# ---------------------------------------------------------------------------

def test_add_transaction_rejects_non_transaction(empty_tracker):
    with pytest.raises(TypeError):
        empty_tracker.add_transaction("not a transaction")


def test_add_transaction_adds_income_and_expense(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(100, "salary"))
    empty_tracker.add_transaction(tracker.Expense(30, "food"))
    assert len(empty_tracker.transactions) == 2


def test_add_expense_within_budget_is_allowed(empty_tracker):
    empty_tracker.set_budget("food", 100)
    empty_tracker.add_transaction(tracker.Expense(100, "food"))
    assert len(empty_tracker.transactions) == 1


def test_add_expense_exactly_at_limit_is_not_exceeded(empty_tracker):
    """Boundary: total_spent == limit must NOT raise (check_limit uses strict '>')."""
    empty_tracker.set_budget("food", 50)
    empty_tracker.add_transaction(tracker.Expense(30, "food"))
    empty_tracker.add_transaction(tracker.Expense(20, "food"))  # total == 50
    assert len(empty_tracker.transactions) == 2


def test_add_expense_one_kopeck_over_limit_raises(empty_tracker):
    """Boundary: exceeding the limit by the smallest unit (0.01) must raise."""
    empty_tracker.set_budget("food", 50)
    empty_tracker.add_transaction(tracker.Expense(50, "food"))
    with pytest.raises(ValueError):
        empty_tracker.add_transaction(tracker.Expense(0.01, "food"))


def test_failed_budget_validation_does_not_add_transaction(empty_tracker):
    """A rejected expense must not leave a partial trace in the transaction list."""
    empty_tracker.set_budget("food", 10)
    with pytest.raises(ValueError):
        empty_tracker.add_transaction(tracker.Expense(20, "food"))
    assert empty_tracker.transactions == []


def test_budget_check_is_case_insensitive(empty_tracker):
    empty_tracker.set_budget("Food", 10)
    with pytest.raises(ValueError):
        empty_tracker.add_transaction(tracker.Expense(20, "FOOD"))


def test_no_budget_set_never_raises(empty_tracker):
    empty_tracker.add_transaction(tracker.Expense(1_000_000, "food"))
    assert len(empty_tracker.transactions) == 1


def test_budget_does_not_restrict_income(empty_tracker):
    empty_tracker.set_budget("salary", 10)
    empty_tracker.add_transaction(tracker.Income(1_000_000, "salary"))
    assert len(empty_tracker.transactions) == 1


# ---------------------------------------------------------------------------
# remove_transaction
# ---------------------------------------------------------------------------

def test_remove_transaction_by_valid_index(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(100, "salary"))
    empty_tracker.add_transaction(tracker.Expense(30, "food"))

    removed = empty_tracker.remove_transaction(1)

    assert removed.category == "salary"
    assert len(empty_tracker.transactions) == 1
    assert empty_tracker.transactions[0].category == "food"


def test_remove_transaction_last_index_boundary(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(100, "salary"))
    empty_tracker.add_transaction(tracker.Expense(30, "food"))

    removed = empty_tracker.remove_transaction(2)

    assert removed.category == "food"
    assert len(empty_tracker.transactions) == 1


@pytest.mark.parametrize("bad_index", [0, -1, -100])
def test_remove_transaction_index_zero_or_negative_raises(empty_tracker, bad_index):
    """index=0 must NOT wrap around to the last element via negative indexing."""
    empty_tracker.add_transaction(tracker.Income(100, "salary"))
    with pytest.raises(IndexError):
        empty_tracker.remove_transaction(bad_index)
    assert len(empty_tracker.transactions) == 1


def test_remove_transaction_index_past_end_raises(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(100, "salary"))
    with pytest.raises(IndexError):
        empty_tracker.remove_transaction(2)


def test_remove_transaction_on_empty_tracker_raises(empty_tracker):
    with pytest.raises(IndexError):
        empty_tracker.remove_transaction(1)


# ---------------------------------------------------------------------------
# calc_balance / calc_income / calc_expense
# ---------------------------------------------------------------------------

def test_calculations_on_empty_tracker_are_zero(empty_tracker):
    assert empty_tracker.calc_balance() == 0
    assert empty_tracker.calc_income() == 0
    assert empty_tracker.calc_expense() == 0


def test_calculations_with_mixed_transactions(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(500, "salary"))
    empty_tracker.add_transaction(tracker.Income(50, "gift"))
    empty_tracker.add_transaction(tracker.Expense(120, "food"))

    assert empty_tracker.calc_income() == 550
    assert empty_tracker.calc_expense() == 120
    assert empty_tracker.calc_balance() == 430


def test_calc_balance_can_go_negative(empty_tracker):
    empty_tracker.add_transaction(tracker.Expense(200, "rent"))
    assert empty_tracker.calc_balance() == -200


# ---------------------------------------------------------------------------
# get_expenses_by_category
# ---------------------------------------------------------------------------

def test_get_expenses_by_category_is_case_insensitive(empty_tracker):
    empty_tracker.add_transaction(tracker.Expense(10, "Food"))
    result = empty_tracker.get_expenses_by_category("FOOD")
    assert len(result) == 1


def test_get_expenses_by_category_excludes_income(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(10, "food"))
    assert empty_tracker.get_expenses_by_category("food") == []


def test_get_expenses_by_category_no_match_returns_empty_list(empty_tracker):
    empty_tracker.add_transaction(tracker.Expense(10, "food"))
    assert empty_tracker.get_expenses_by_category("rent") == []


# ---------------------------------------------------------------------------
# to_list / from_data
# ---------------------------------------------------------------------------

def test_to_list_and_from_data_roundtrip(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(500, "salary"))
    empty_tracker.add_transaction(tracker.Expense(44.7, "food"))

    data = empty_tracker.to_list()
    rebuilt = tracker.ExpenseTracker.from_data(data)

    assert len(rebuilt.transactions) == 2
    assert rebuilt.calc_balance() == empty_tracker.calc_balance()
    assert rebuilt.transactions[1].amount == 44.7


def test_from_data_empty_list_produces_empty_tracker():
    rebuilt = tracker.ExpenseTracker.from_data([])
    assert rebuilt.transactions == []


# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------

def test_str_on_empty_tracker(empty_tracker):
    assert "empty" in str(empty_tracker).lower()


def test_str_on_non_empty_tracker_contains_rows(empty_tracker):
    empty_tracker.add_transaction(tracker.Income(500, "salary"))
    output = str(empty_tracker)
    assert "salary" in output
    assert "Income" in output


# ---------------------------------------------------------------------------
# BudgetManager
# ---------------------------------------------------------------------------

def test_get_budget_limits_with_no_expenses_yet(empty_tracker):
    empty_tracker.set_budget("food", 100)
    limits = empty_tracker.get_budget_limits()
    assert limits == [("food", 0, 100)]


def test_set_budget_overwrites_previous_limit(empty_tracker):
    empty_tracker.set_budget("food", 50)
    empty_tracker.set_budget("food", 200)
    empty_tracker.add_transaction(tracker.Expense(100, "food"))
    limits = empty_tracker.get_budget_limits()
    assert limits == [("food", 100, 200)]


def test_get_budget_limits_only_counts_matching_category(empty_tracker):
    empty_tracker.set_budget("food", 100)
    empty_tracker.add_transaction(tracker.Expense(30, "food"))
    empty_tracker.add_transaction(tracker.Expense(1000, "rent"))

    limits = empty_tracker.get_budget_limits()
    assert limits == [("food", 30, 100)]
