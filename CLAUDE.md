# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AuraFi is a personal finance CLI tool (Python) being evolved in phases into a full-stack web app (planned: Django + DRF + PostgreSQL). Current state (`Phase04` branch) is a console app backed by SQLite with email/password login — see README.md for the full phase roadmap and per-phase changelog.

## Commands

```bash
# Configure environment (first run)
cp .env.example .env

# Seed a demo user + sample data (first run, or to reset the database)
python3 seed.py

# Run the CLI app
python3 main.py

# Run the full test suite (CI does this with PYTHONPATH=$PWD, run from repo root)
python -m pytest tests/ -v

# Run a single test file / test
python -m pytest tests/test_models.py -v
python -m pytest tests/test_models.py::TestSetBudget::test_second_call_updates_limit_instead_of_duplicating -v

# Install dependencies (venv is aura_venv/, not committed logic-wise but present locally)
pip install -r requirements.txt
```

There is no lint/format tooling configured and no `pytest.ini`/`pyproject.toml` — pytest runs with defaults, so imports rely on running from the repo root (or `PYTHONPATH` including it), matching `.github/workflows/ci.yml`.

## Architecture

**Layered, not flat**: the database is dumb storage only; all business logic (budget validation, balance/category calculations, kopecks precision) lives in `expense_tracker/`'s domain classes; `main.py` only ever talks to those classes, never to the DB layer directly (except `login`/`authenticate_user`, which has no domain-object home).

**Package layout (independent packages/modules under repo root, no `src/` layout):**
- `database.py` — `DB_PATH`/`INIT_SQL_PATH` resolved relative to this file's own directory (not the caller's cwd), loaded from `.env` (`DB_NAME`) via a tiny built-in loader (no external dependency). `init_db()` runs `init.sql`'s DDL (`users`/`transactions`/`budgets`). `get_connection()` and the `db_connection()` context manager both log and re-raise `sqlite3.Error` — every `models.py` function goes through `db_connection()` so DB-connection problems are never silently swallowed.
- `models.py` (root level) — **the DB-access module**: plain CRUD functions only, no business rules. `create_user`/`authenticate_user` (PBKDF2-HMAC-SHA256 hashed passwords, stdlib only), `add_transaction`, `get_all_transactions`, `get_balance`, `get_expenses_by_category`, `set_budget`, `get_categories`, `get_budget_limits`, `delete_transaction`, `check_budget_status`, plus `DEFAULT_EXPENSE_CATEGORIES`/`DEFAULT_INCOME_CATEGORIES` (a **one-time seed** `create_user()` writes on account creation — not a live source anyone reads from later). Called from two places only: `expense_tracker`'s classes (on a state change) and `main.py`'s `login()`/`seed.py` (account-level concerns with no domain-object home).
- `init.sql` — table DDL, executed by `database.init_db()`.
- `expense_tracker/` — the domain layer, holds all the actual logic:
  - `models.py` — `Transaction`/`Income`/`Expense`/`Budget`, money as **integer kopecks** internally (`to_kopecks()`/`to_display()`), converted to/from the DB's plain hryvnia `REAL` only at the boundary (`Transaction.from_row()` on load, `.amount` on save). `Transaction.__add__`/`__radd__` return signed kopecks via `signed_amount`, so `sum(transactions)` works.
  - `tracker.py` — `ExpenseTracker` (owns `self.transactions`, in-memory) and `BudgetManager` (owns `self.budgets`, in-memory). **Every mutating method persists its own change**: `ExpenseTracker.add_transaction()` validates the budget, then calls `models.add_transaction()` (via `import models as db`) and only appends to `self.transactions` after that succeeds (so the object gets a real DB id); `remove_transaction()` pops locally and calls `models.delete_transaction()`; `BudgetManager.set_budget()` updates `self.budgets` and calls `models.set_budget()`. Reads (`calc_balance`, `get_budget_limits`, category breakdowns) are pure in-memory computation over what's already loaded — no DB round-trip. `ExpenseTracker.from_db(user_id)` is the one place that *reads* from the DB module, to hydrate a tracker at login.
  - `cli.py` — presentation only: `input_transaction(transaction_type, categories)` builds the numbered category menu from a `{category: monthly_limit}` dict (sourced from `tracker.get_categories()`) and gathers amount+category. No category or money data of its own.
- `cli/` — generic terminal I/O only (not domain-specific). `output.py` defines `Outer`, a chainable colored-string builder (`Outer.append_green("x").append_yellow("y").print()`) backed by `ColorText`/`ColorAction` descriptors and ANSI codes in `colorss.py`. `input.py` wraps `input()` with type coercion, a `'q'`-to-cancel convention, and `input_category()` (numbered-menu picker).
- `logger/` — thin wrapper around stdlib `logging`, configured once in `config.py` (writes to `app.log`) and exposed via `logger.get_logger(__name__)`.
- `seed.py` — resets `aurafi.db` and inserts one demo user (credentials from `.env`: `SEED_USERNAME`/`SEED_EMAIL`/`SEED_PASSWORD`) with 5 sample transactions and 2 budgets; calls the root `models.py` DB functions directly (not through `ExpenseTracker`) on purpose — it deliberately backdates an already-over-budget scenario for the demo, which `ExpenseTracker.add_transaction()`'s live validation would reject.

**`main.py` is the composition root**: `main()` calls `init_db()`, `login()` (prompts email/password, calls `models.authenticate_user`/`get_username_by_email` — the one place outside `expense_tracker` allowed to call the DB module directly, since there's no user-session domain object), then `ExpenseTracker.from_db(user_id)`, then runs the menu loop against that one `tracker` object for the rest of the session. Every action (`add_transaction_entry`, `delete_transaction_entry`, `show_all_transactions*`) takes `tracker`, not `user_id`. `sqlite3.Error` is caught around `init_db()`, `login()`, `ExpenseTracker.from_db()`, and each menu command dispatch, so a database problem logs + shows a message instead of crashing — this still works with the layered design because `db.*` errors simply propagate up through the tracker's methods.

**Single source of truth for categories lives in the database** (`budgets` table — see schema note in `init.sql`), not in a Python constant: `create_user()` seeds `DEFAULT_EXPENSE_CATEGORIES`/`DEFAULT_INCOME_CATEGORIES` into it exactly **once**, atomically, when the user is created (pass `seed_default_categories=False` for a blank-slate user, e.g. in tests). `BudgetManager.load()` reads the full category list fresh in `ExpenseTracker.from_db()`; `BudgetManager.set_budget()` is the only path that changes it afterward, and it always writes through to the DB in the same call. `budgets.transaction_type` ('income'/'expense') + nullable `monthly_limit` (always `NULL` for income — no budget concept there) let one table serve both the expense-budget feature and the income category list.

**Budget enforcement**: `ExpenseTracker.add_transaction()` calls `BudgetManager.validate_expense()` *before* persisting; it raises `ValueError` if the category's limit (strict `>`, exact match allowed) would be exceeded, and the transaction is never inserted (not in memory, not in the DB). **Known gap**: `Budget.check_limit()` sums all-time spend, not the current month, even though budgets are presented as monthly — root `models.py`'s `check_budget_status()` already implements correct month-scoping (`strftime('%Y-%m', ...)`) but isn't wired into `BudgetManager` yet (only used by `seed.py`'s report).

**Case-insensitive categories**: normalized to lowercase at write time (`models.add_transaction`, `models.set_budget`, and `BudgetManager`/`Transaction` category handling) and compared via `LOWER(...)` at query time in the root `models.py` queries — both layers matter, since the write-time normalization prevents new duplicate rows but the query-time `LOWER()` is what protects against any pre-existing mixed-case data.

**Testing DB access**: `tests/conftest.py`'s `temp_db` fixture creates an isolated SQLite file under pytest's `tmp_path`, runs `init_db()` against it, and monkeypatches `models.db_connection` so every call into the root `models.py` module — whether direct or via `expense_tracker.tracker`'s `import models as db` — is redirected there. The real `aurafi.db` is never touched, and `tmp_path` cleanup means nothing needs manual rollback. Use this fixture for any new test that touches persistence.
