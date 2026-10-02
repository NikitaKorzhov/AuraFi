import logging

import pytest

import expense_tracker as et
from expense_tracker import cli


@pytest.fixture
def write_spy(monkeypatch):
    """Replaces cli.write_transactions with a recorder so tests never touch the real
    transactions.json on disk; appends the exact list passed to it on each call."""
    calls = []
    monkeypatch.setattr(cli, "write_transactions", lambda data, *a, **k: calls.append(data))
    return calls


# ---------------------------------------------------------------------------
# is_cancel_requested
# ---------------------------------------------------------------------------

class TestIsCancelRequested:
    def test_lowercase_q_requests_cancellation_and_prints_message(self, capsys):
        assert cli.is_cancel_requested("q") is True
        assert "canceled" in capsys.readouterr().out.lower()

    @pytest.mark.parametrize("char", ["Q", "n", "", " ", "quit"])
    def test_anything_other_than_lowercase_q_is_not_cancellation(self, capsys, char):
        """Case-sensitive by design (unlike cli.input's own 'q' handling, which lowercases
        first) — an uppercase 'Q' is NOT treated as a cancel request here, and nothing is
        printed for a non-cancel character."""
        assert cli.is_cancel_requested(char) is False
        assert capsys.readouterr().out == ""

    def test_none_does_not_raise(self):
        assert cli.is_cancel_requested(None) is False


# ---------------------------------------------------------------------------
# input_transaction
# ---------------------------------------------------------------------------

class TestInputTransaction:
    def test_returns_none_and_logs_when_user_cancels(self, monkeypatch, caplog, capsys):
        monkeypatch.setattr(cli, "input_transaction1", lambda d: None)

        with caplog.at_level(logging.WARNING, logger="expense_tracker.cli"):
            result = cli.input_transaction("income")

        assert result is None
        assert any("canceled" in r.message.lower() for r in caplog.records)
        assert "canceled" in capsys.readouterr().out.lower()

    def test_treats_any_falsy_result_as_cancellation(self, monkeypatch):
        """`if not transaction:` treats ANY falsy value, not just None, as a cancellation —
        an empty dict from input_transaction1 is (incorrectly) indistinguishable from a
        real cancel here."""
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {})
        assert cli.input_transaction("income") is None

    @pytest.mark.parametrize("transaction_type", ["income", "expense"])
    def test_attaches_type_for_known_transaction_types(self, monkeypatch, transaction_type):
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {"amount": 10, "category": "food"})
        result = cli.input_transaction(transaction_type)
        assert result["type"] == transaction_type

    @pytest.mark.parametrize("transaction_type", ["", "unknown", "transfer"])
    def test_does_not_attach_type_for_unrecognized_transaction_types(self, monkeypatch, transaction_type):
        """Edge case: for any transaction_type outside {"income", "expense"} (including the
        default ""), the returned dict silently has no "type" key at all."""
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {"amount": 10, "category": "food"})
        result = cli.input_transaction(transaction_type)
        assert "type" not in result


# ---------------------------------------------------------------------------
# add_transaction
# ---------------------------------------------------------------------------

class TestAddTransaction:
    def test_does_nothing_when_input_is_cancelled(self, monkeypatch, write_spy):
        tracker = et.ExpenseTracker()
        monkeypatch.setattr(cli, "input_transaction", lambda t: None)

        cli.add_transaction(tracker, "income")

        assert tracker.transactions == []
        assert write_spy == []

    def test_adds_and_persists_successfully(self, monkeypatch, write_spy):
        tracker = et.ExpenseTracker()
        monkeypatch.setattr(
            cli, "input_transaction", lambda t: {"amount": 500, "category": "salary", "type": "income"}
        )

        cli.add_transaction(tracker, "income")

        assert len(tracker.transactions) == 1
        assert tracker.transactions[0].category == "salary"
        assert write_spy == [tracker.to_list()]

    def test_expense_exactly_at_budget_limit_is_allowed_and_persisted(self, monkeypatch, write_spy):
        """Boundary: check_limit() uses strict '>', so landing exactly on the limit must succeed."""
        tracker = et.ExpenseTracker()
        tracker.set_budget("food", 50)
        tracker.add_transaction(et.Expense(30, "food"))
        monkeypatch.setattr(
            cli, "input_transaction", lambda t: {"amount": 20, "category": "food", "type": "expense"}
        )

        cli.add_transaction(tracker, "expense")

        assert len(tracker.transactions) == 2
        assert write_spy == [tracker.to_list()]

    def test_expense_over_budget_limit_is_rejected_and_not_persisted(self, monkeypatch, write_spy, caplog):
        tracker = et.ExpenseTracker()
        tracker.set_budget("food", 50)
        monkeypatch.setattr(
            cli, "input_transaction", lambda t: {"amount": 100, "category": "food", "type": "expense"}
        )

        with caplog.at_level(logging.ERROR, logger="expense_tracker.cli"):
            cli.add_transaction(tracker, "expense")

        assert tracker.transactions == []
        assert write_spy == []
        assert any("budget limit exceeded" in r.message.lower() for r in caplog.records)

    def test_unrecognized_transaction_type_crashes_with_keyerror(self, monkeypatch, write_spy):
        """Latent bug, not a desired behavior: main.py only ever calls add_transaction with
        "income"/"expense", but if it (or future code) passed any other type, input_transaction
        would omit the "type" key and Transaction.from_input() would blow up with a KeyError
        instead of failing gracefully."""
        tracker = et.ExpenseTracker()
        monkeypatch.setattr(cli, "input_transaction1", lambda d: {"amount": 10, "category": "food"})

        with pytest.raises(KeyError):
            cli.add_transaction(tracker, "transfer")

        assert tracker.transactions == []
        assert write_spy == []


# ---------------------------------------------------------------------------
# show_all_transactions / show_all_transactions_with_info
# ---------------------------------------------------------------------------

class TestShowAllTransactions:
    def test_empty_tracker_falls_through_to_tracker_str_not_the_empty_message(self, capsys):
        """ExpenseTracker defines no __bool__/__len__, so objects are truthy by default and
        `if not tracker:` is always False — the "No transactions found." branch is dead code,
        and even a brand-new empty tracker falls through to printing its own __str__."""
        tracker = et.ExpenseTracker()

        cli.show_all_transactions(tracker)

        out = capsys.readouterr().out
        assert "no transactions found" not in out.lower()
        assert "empty" in out.lower()

    def test_non_empty_tracker_prints_transaction_rows(self, capsys):
        tracker = et.ExpenseTracker()
        tracker.add_transaction(et.Income(500, "salary"))

        cli.show_all_transactions(tracker)

        assert "salary" in capsys.readouterr().out.lower()


class TestShowAllTransactionsWithInfo:
    def test_empty_tracker_with_no_budgets_shows_zero_sums_and_no_budget_line(self, capsys):
        tracker = et.ExpenseTracker()

        cli.show_all_transactions_with_info(tracker)

        out = capsys.readouterr().out
        assert "Income sum: 0" in out
        assert "Expense sum: 0" in out
        assert "total:0" in out

    def test_budget_with_no_spending_shows_zero_spent(self, capsys):
        tracker = et.ExpenseTracker()
        tracker.set_budget("food", 100)

        cli.show_all_transactions_with_info(tracker)

        assert "food: 0 / 100" in capsys.readouterr().out

    def test_budget_with_spending_shows_accumulated_total(self, capsys):
        tracker = et.ExpenseTracker()
        tracker.set_budget("food", 100)
        tracker.add_transaction(et.Expense(30, "food"))

        cli.show_all_transactions_with_info(tracker)

        assert "food: 30 / 100" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# delete_transaction
# ---------------------------------------------------------------------------

class TestDeleteTransaction:
    def test_empty_tracker_always_prompts_instead_of_showing_the_empty_message(
        self, monkeypatch, capsys, write_spy
    ):
        """Same dead-code issue as show_all_transactions: `if not tracker:` never triggers the
        "No transactions to delete." message, even for a brand-new empty tracker — it always
        shows the (empty) list and prompts for an index."""
        tracker = et.ExpenseTracker()
        monkeypatch.setattr(cli, "input_index_to_delete", lambda *a, **k: None)

        cli.delete_transaction(tracker)

        out = capsys.readouterr().out
        assert "no transactions to delete" not in out.lower()
        assert write_spy == []

    def test_cancel_during_prompt_removes_nothing(self, monkeypatch, write_spy):
        tracker = et.ExpenseTracker()
        tracker.add_transaction(et.Income(100, "salary"))
        monkeypatch.setattr(cli, "input_index_to_delete", lambda *a, **k: None)

        cli.delete_transaction(tracker)

        assert len(tracker.transactions) == 1
        assert write_spy == []

    @pytest.mark.parametrize("idx", [1, 2])
    def test_valid_boundary_indices_remove_and_persist(self, monkeypatch, write_spy, idx):
        """Boundary: both the first (1) and last (len) user-facing indices must work."""
        tracker = et.ExpenseTracker()
        tracker.add_transaction(et.Income(100, "salary"))
        tracker.add_transaction(et.Expense(30, "food"))
        monkeypatch.setattr(cli, "input_index_to_delete", lambda *a, **k: idx)

        cli.delete_transaction(tracker)

        assert len(tracker.transactions) == 1
        assert write_spy == [tracker.to_list()]

    @pytest.mark.parametrize("idx", [0, -1, 3, 100])
    def test_out_of_range_indices_are_rejected_without_mutation(self, monkeypatch, write_spy, caplog, idx):
        """Boundary: index=0 must not be accepted (range check is 0 < idx <= len), and indices
        past the end or negative must also be rejected without touching the tracker or writing."""
        tracker = et.ExpenseTracker()
        tracker.add_transaction(et.Income(100, "salary"))
        tracker.add_transaction(et.Expense(30, "food"))
        monkeypatch.setattr(cli, "input_index_to_delete", lambda *a, **k: idx)

        with caplog.at_level(logging.ERROR, logger="expense_tracker.cli"):
            cli.delete_transaction(tracker)

        assert len(tracker.transactions) == 2
        assert write_spy == []
        assert any("out of range" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# write_transactions / read_transactions
# ---------------------------------------------------------------------------

class TestWriteAndReadTransactions:
    def test_default_file_path_constant(self):
        assert cli.FILE_PATH == "transactions.json"

    def test_round_trip_simple_data(self, tmp_path):
        path = tmp_path / "transactions.json"
        data = [
            {"amount": 50000, "type": "income", "category": "salary"},
            {"amount": 3000, "type": "expense", "category": "food"},
        ]

        cli.write_transactions(data, file_path=str(path))

        assert cli.read_transactions(file_path=str(path)) == data

    def test_write_empty_list_then_read_back_empty_list(self, tmp_path):
        path = tmp_path / "transactions.json"

        cli.write_transactions([], file_path=str(path))

        assert path.read_text(encoding="utf-8").strip() == "[]"
        assert cli.read_transactions(file_path=str(path)) == []

    def test_read_nonexistent_file_returns_empty_list(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        assert cli.read_transactions(file_path=str(missing)) == []

    def test_read_invalid_json_logs_error_and_returns_empty_list(self, tmp_path, caplog):
        path = tmp_path / "broken.json"
        path.write_text("{not valid json", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger="expense_tracker.cli"):
            result = cli.read_transactions(file_path=str(path))

        assert result == []
        assert any("error while reading" in r.message.lower() for r in caplog.records)

    def test_read_empty_file_is_treated_as_invalid_json(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("", encoding="utf-8")

        assert cli.read_transactions(file_path=str(path)) == []

    def test_write_sanitizes_invalid_surrogate_characters_in_strings(self, tmp_path):
        """ensure_ascii=False makes json.dump write raw unicode straight into the utf-8 file,
        so an unpaired surrogate (e.g. from mangled input) would raise UnicodeEncodeError on
        write without the encode/decode('utf-8', 'ignore') cleaning applied to every string
        field first."""
        path = tmp_path / "transactions.json"
        data = [{"amount": 100, "type": "expense", "category": "food\ud800"}]

        cli.write_transactions(data, file_path=str(path))  # must not raise

        result = cli.read_transactions(file_path=str(path))
        assert result[0]["category"] == "food"

    def test_write_preserves_non_string_values_unchanged(self, tmp_path):
        path = tmp_path / "transactions.json"
        data = [{"amount": 12345, "type": "income", "category": "salary", "flag": True, "extra": None}]

        cli.write_transactions(data, file_path=str(path))

        assert cli.read_transactions(file_path=str(path)) == data

    def test_read_raises_for_a_directory_path(self, tmp_path):
        """Documents a gap: only json.JSONDecodeError is caught, so any other OSError (e.g.
        file_path pointing at a directory, or a permissions issue) propagates instead of the
        function falling back to an empty list."""
        with pytest.raises(IsADirectoryError):
            cli.read_transactions(file_path=str(tmp_path))
