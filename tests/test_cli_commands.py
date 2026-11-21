from __future__ import annotations

from pathlib import Path

import pytest

import models
from cli_commands import build_parser
from config import get_settings
from expense_tracker import ExpenseTracker
from main import dispatch_command


# ---------------------------------------------------------------------------
# build_parser — argparse behavior (no DB needed)
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["--help"])
        assert exc.value.code == 0

    def test_version_exits_zero(self):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["--version"])
        assert exc.value.code == 0

    def test_add_missing_required_arg_exits_nonzero_not_traceback(self, capsys):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["add", "expense"])
        assert exc.value.code == 2
        assert "amount" in capsys.readouterr().err.lower()

    def test_add_bad_amount_type_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["add", "expense", "--amount", "abc", "--category", "Food"])
        assert exc.value.code == 2

    def test_add_parses_expected_namespace(self):
        args = build_parser().parse_args(["add", "income", "--amount", "500", "--category", "Salary"])
        assert args.command == "add"
        assert args.transaction_type == "income"
        assert args.amount == 500.0
        assert args.category == "Salary"

    def test_budget_set_requires_nested_subcommand(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["budget"])

    def test_user_id_defaults_from_settings(self):
        args = build_parser().parse_args(["balance"])
        assert args.user_id == get_settings()["cli_user_id"]

    def test_dry_run_flag(self):
        args = build_parser().parse_args(["--dry-run", "delete", "--id", "1"])
        assert args.dry_run is True


# ---------------------------------------------------------------------------
# dispatch_command — the real business logic, against a throwaway DB
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker(temp_db):
    user_id = models.create_user("alice", "alice@example.com", "pw", seed_default_categories=False)
    return ExpenseTracker.from_db(user_id)


@pytest.fixture
def settings():
    s = get_settings()
    s["export_dir"] = "exports_test/"
    return s


class TestDispatchAdd:
    def test_add_income_persists_and_prints_confirmation(self, tracker, settings, capsys):
        args = build_parser().parse_args(["add", "income", "--amount", "500", "--category", "Salary"])
        dispatch_command(args, tracker, settings)

        assert "500.00" in capsys.readouterr().out
        assert len(tracker.transactions) == 1
        assert tracker.transactions[0].category == "Salary"

    def test_add_missing_date_defaults_to_today_not_none(self, tracker, settings, capsys):
        args = build_parser().parse_args(["add", "income", "--amount", "500", "--category", "Salary"])
        dispatch_command(args, tracker, settings)

        assert "None" not in capsys.readouterr().out
        assert tracker.transactions[0].date is not None

    def test_add_dry_run_does_not_persist(self, tracker, settings, capsys):
        args = build_parser().parse_args(
            ["--dry-run", "add", "income", "--amount", "500", "--category", "Salary"]
        )
        dispatch_command(args, tracker, settings)

        assert "DRY RUN" in capsys.readouterr().out
        assert tracker.transactions == []

    def test_add_expense_over_budget_is_rejected(self, tracker, settings, capsys):
        tracker.set_budget("food", "expense", 100)
        args = build_parser().parse_args(["add", "expense", "--amount", "150", "--category", "food"])
        dispatch_command(args, tracker, settings)

        out = capsys.readouterr().out
        assert "❌" in out
        assert tracker.transactions == []


class TestDispatchList:
    def test_list_filters_by_category(self, tracker, settings, capsys):
        from expense_tracker import Expense, Income

        tracker.add_transaction(Income(500, "salary"))
        tracker.add_transaction(Expense(100, "food"))

        args = build_parser().parse_args(["list", "--category", "food"])
        dispatch_command(args, tracker, settings)

        out = capsys.readouterr().out
        assert "food" in out
        assert "salary" not in out

    def test_list_empty_shows_message(self, tracker, settings, capsys):
        args = build_parser().parse_args(["list"])
        dispatch_command(args, tracker, settings)
        assert "не знайдено" in capsys.readouterr().out


class TestDispatchBalance:
    def test_balance_reflects_transactions(self, tracker, settings, capsys):
        from expense_tracker import Expense, Income

        tracker.add_transaction(Income(500, "salary"))
        tracker.add_transaction(Expense(120, "food"))

        args = build_parser().parse_args(["balance"])
        dispatch_command(args, tracker, settings)

        assert "380.00" in capsys.readouterr().out


class TestDispatchBudget:
    def test_set_then_show_includes_utilization(self, tracker, settings, capsys):
        from expense_tracker import Expense

        set_args = build_parser().parse_args(["budget", "set", "--category", "food", "--limit", "100"])
        dispatch_command(set_args, tracker, settings)
        capsys.readouterr()

        tracker.add_transaction(Expense(50, "food"))
        show_args = build_parser().parse_args(["budget", "show"])
        dispatch_command(show_args, tracker, settings)

        out = capsys.readouterr().out
        assert "food" in out
        assert "50.0%" in out

    def test_show_warns_past_threshold(self, tracker, settings, capsys):
        from expense_tracker import Expense

        tracker.set_budget("food", "expense", 100)
        tracker.add_transaction(Expense(90, "food"))  # 90% > default 80% warn_budget_pct

        args = build_parser().parse_args(["budget", "show"])
        dispatch_command(args, tracker, settings)

        assert "⚠️" in capsys.readouterr().out

    def test_set_dry_run_does_not_persist(self, tracker, settings, capsys):
        args = build_parser().parse_args(["--dry-run", "budget", "set", "--category", "food", "--limit", "100"])
        dispatch_command(args, tracker, settings)

        assert "DRY RUN" in capsys.readouterr().out
        assert tracker.get_categories("expense") == {}


class TestDispatchDelete:
    def test_delete_existing_removes_it(self, tracker, settings, capsys):
        from expense_tracker import Income

        tracker.add_transaction(Income(500, "salary"))
        tx_id = tracker.transactions[0].id

        args = build_parser().parse_args(["delete", "--id", str(tx_id)])
        dispatch_command(args, tracker, settings)

        assert "видалено" in capsys.readouterr().out
        assert tracker.transactions == []

    def test_delete_nonexistent_reports_not_found(self, tracker, settings, capsys):
        args = build_parser().parse_args(["delete", "--id", "999999"])
        dispatch_command(args, tracker, settings)
        assert "не знайдено" in capsys.readouterr().out


class TestDispatchReport:
    def test_report_totals_for_current_month(self, tracker, settings, capsys):
        from datetime import date

        from expense_tracker import Expense, Income

        today = date.today().isoformat()
        tracker.add_transaction(Income(500, "salary", date=today))
        tracker.add_transaction(Expense(120, "food", date=today))
        tracker.add_transaction(Expense(99999, "food", date="2000-01-01"))  # different month — excluded

        args = build_parser().parse_args(["report"])
        dispatch_command(args, tracker, settings)

        out = capsys.readouterr().out
        assert "+500.00" in out
        assert "-120.00" in out
        assert "380.00" in out


class TestDispatchExport:
    def test_export_csv_writes_real_string_values_not_enum_repr(self, tracker, settings, capsys, tmp_path):
        from expense_tracker import Income

        settings["export_dir"] = str(tmp_path / "exports")
        tracker.add_transaction(Income(500, "salary"))

        args = build_parser().parse_args(["export", "--format", "csv"])
        dispatch_command(args, tracker, settings)

        content = (Path(settings["export_dir"]) / "transactions.csv").read_text(encoding="utf-8")
        assert ",income," in content
        assert "TransactionType" not in content

    def test_export_json_writes_real_string_values(self, tracker, settings, capsys, tmp_path):
        import json

        from expense_tracker import Expense

        settings["export_dir"] = str(tmp_path / "exports")
        tracker.add_transaction(Expense(50, "food"))

        args = build_parser().parse_args(["export", "--format", "json"])
        dispatch_command(args, tracker, settings)

        data = json.loads((Path(settings["export_dir"]) / "transactions.json").read_text(encoding="utf-8"))
        assert data[0]["type"] == "expense"
