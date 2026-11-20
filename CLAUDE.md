# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AuraFi is a personal finance CLI tool (Python) being evolved in phases into a full-stack web app (planned: Django + DRF + SQLite/PostgreSQL). Current state (`Phase3` branch) is a console app with JSON file persistence — see README.md for the full phase roadmap and per-phase changelog.

## Commands

```bash
# Run the CLI app
python3 main.py

# Run the full test suite (CI does this with PYTHONPATH=$PWD, run from repo root)
python -m pytest tests/ -v

# Run a single test file / test
python -m pytest tests/test_tracker.py -v
python -m pytest tests/test_tracker.py::test_add_expense_within_budget_is_allowed -v

# Install dependencies (venv is aura_venv/, not committed logic-wise but present locally)
pip install -r requirements.txt
```

There is no lint/format tooling configured and no `pytest.ini`/`pyproject.toml` — pytest runs with defaults, so imports rely on running from the repo root (or `PYTHONPATH` including it), matching `.github/workflows/ci.yml`.

## Architecture

**Money is always stored as integer kopecks internally**, never floats. `expense_tracker/models.py` has `to_kopecks()`/`to_display()` module-level converters; every `Transaction`/`Budget` stores `*_kopecks` and exposes a `.amount`/`.monthly_limit` property that converts for display. When adding new money-related fields, follow this same pattern rather than storing floats directly — this avoids rounding errors in totals/budget checks.

**Package layout (3 independent packages under repo root, no `src/` layout):**
- `expense_tracker/` — domain logic, no I/O. `models.py` (`Transaction`/`Income`/`Expense`/`Budget`), `tracker.py` (`ExpenseTracker` owns the transaction list and delegates budget enforcement to `BudgetManager`), `constants.py` (`TransactionCategory` enum, currently unused by the rest of the code). Public API is re-exported through `expense_tracker/__init__.py` — import from there (`import expense_tracker as tracker`), not from the submodules, as the tests do.
- `cli/` — presentation only. `output.py` defines `Outer`, a chainable colored-string builder (`Outer.append_green("x").append_yellow("y").print()`) backed by `ColorText`/`ColorAction` descriptors and ANSI codes in `colorss.py`. `input.py` wraps `input()` with type coercion and a `'q'`-to-cancel convention used throughout the CLI flows.
- `logger/` — thin wrapper around stdlib `logging`, configured once in `config.py` (writes to `app.log`) and exposed via `logger.get_logger(__name__)`.

**`main.py` is the composition root**: it wires `expense_tracker`, `cli`, and `logger` together, handles JSON persistence (`read_transactions`/`write_transactions` against `transactions.json`), and runs the menu loop. There's a global module-level `transactions: ExpenseTracker` instance built from disk on startup — most functions in `main.py` act on that global rather than taking it as a parameter.

**Two-constructor pattern on `Transaction`**: `Transaction.from_input(dict)` builds from raw user input (hryvnia amount, needs kopecks conversion) while `Transaction.from_data(dict)` / `_from_kopecks()` rebuilds from already-converted stored data (loaded from `transactions.json`). Picking the wrong one double-converts or under-converts amounts — use `from_input` only for fresh user-entered data, `from_data` only for round-tripping persisted data.

**Budget enforcement flow**: `ExpenseTracker.add_transaction()` calls `BudgetManager.validate_expense()` *before* appending, which raises `ValueError` if the category's monthly limit (strict `>`, exact match is allowed) would be exceeded — the transaction is never added in that case. Budget categories are matched case-insensitively (always lower-cased on both set and lookup). Budgets are currently hardcoded in `main()` at startup (no CLI to manage them yet).

**Transaction arithmetic**: `Transaction.__add__`/`__radd__` return a signed kopecks integer (not a `Transaction`), via the `signed_amount` property (`Income` positive, `Expense` negative). This is what makes `sum(transactions_list)` work for balance calculations in `ExpenseTracker.calc_balance()`.
