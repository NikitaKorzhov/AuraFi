# AuraFi

**AuraFi** is a scalable personal finance management platform that evolves from a lightweight Python CLI utility into a robust, full-stack web application. Designed with modern architecture in mind, it bridges the gap between fast local utility logging and comprehensive visual data analytics.

### 🌟 Key Capabilities
* **Flexible Tracking:** Seamlessly manage income and expenses across customizable categories.
* **Data Transparency:** Inspect transactions through structured data tables and clean state models.
* **Visual Insights:** Gain deep control over your budget via interactive financial dashboards.

## ⚙️ Getting Started

### 1. Install dependencies
```bash
python3 -m venv aura_venv
source aura_venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
Copy the example env file and adjust values if you want:
```bash
cp .env.example .env
```

| Variable | Purpose | Default |
|---|---|---|
| `PG_HOST` | PostgreSQL server host | `127.0.0.1` |
| `PG_PORT` | PostgreSQL server port | `5432` |
| `PG_DB` | PostgreSQL database name (created automatically if missing) | `aurafi` |
| `PG_USER` | PostgreSQL role | `postgres` |
| `PG_PASSWORD` | PostgreSQL password (leave empty for local trust auth) | *(empty)* |
| `SEED_USERNAME` | Demo user's username (created by `seed.py`) | `demo_user` |
| `SEED_EMAIL` | Demo user's login email (created by `seed.py`) | `demo@example.com` |
| `SEED_PASSWORD` | Demo user's login password | `changeme123` |

`.env.example` ships with different placeholder values on purpose — put your own real values in `.env` (gitignored), don't copy the example ones as-is.

Requires a running local PostgreSQL server (Postgres.app, Homebrew `postgresql`, Docker, etc.) — `database.init_db()` creates the `PG_DB` database itself on first run, but the server has to already be up and reachable at `PG_HOST`/`PG_PORT`.

### 3. Seed demo data (first run)
```bash
python3 seed.py
```
Creates the database, one demo user with 5 sample transactions and 2 budgets, and prints a report plus the login credentials to use in the next step.

### 4. Run the app
```bash
python3 main.py
```
Log in with the email/password from `.env` (or the ones `seed.py` printed), then use the menu to add, view, and delete income/expense transactions.

### 5. Run the test suite
```bash
PYTHONPATH=$PWD python -m pytest tests/ -v
```

## 🚀 Project Roadmap

* **Phase 1-3 (Core Python & Storage):** ✅ Done
  * CLI menu loop for adding, listing, and deleting income/expense transactions.
  * OOP domain model (`Transaction`/`Income`/`Expense`/`Budget`/`ExpenseTracker`) with category-based monthly budget limits.
  * Local JSON persistence (`transactions.json`), colored console output (`cli/`), structured logging (`logger/`), and the first pytest suite.

* **Phase 4-5 (Testing & Databases):** 🚧 In progress
  * ✅ Relational persistence (`database.py` / root `models.py` / `init.sql`) replacing `transactions.json` — originally SQLite, migrated to **PostgreSQL** (Homework 30; same table structure, now the live backend — see `postgres/` for the standalone homework scripts this was built from).
  * ✅ Layered architecture: `expense_tracker/`'s OOP classes (`ExpenseTracker`/`BudgetManager`) own all business logic and persist every state change through the DB-access module; the database itself stores data only.
  * ✅ User accounts with hashed-password login (`users` table).
  * ✅ Category selection menu, with categories and budgets stored only in the database — single source of truth, no parallel Python category list.
  * ✅ Case-insensitive category matching.
  * ✅ Centralized database connection error handling and logging (`db_connection()`).
  * ✅ `.env`-based configuration for the PostgreSQL connection and seed login credentials.
  * ✅ Automated test suite with an isolated-DB fixture (`tests/conftest.py`'s `temp_db`, now backed by a throwaway PostgreSQL database per test) covering the full DB-backed flow.
  * ⬜ Currency conversion (multi-currency support / exchange rates).
  * ⬜ Monthly (not all-time) budget-limit enforcement when adding an expense.

* **Phase 6-7 (Web & API):** ⬜ Planned
  * Full-stack web application with Django.
  * Dynamic dashboards for transactions, balances, and budgets.
  * REST API endpoints via Django REST Framework.

* **Phase 8 (Polish & Deploy):** ⬜ Planned
  * Clean architecture / production-grade refactor.
  * Advanced analytics and reporting.
  * Production deployment.

## 📌 Phase 1 Branch Progress
* **CLI Foundation:** Built the core menu-driven console loop — add income/expense, list, and delete transactions.
* **Persistent Storage:** Transactions are saved to and loaded from a local JSON file between sessions.
* **Colored Console Output:** Introduced a reusable `color_string()` helper for consistent, readable terminal feedback.
* **Error Logging:** Runtime issues are written to a log file instead of failing silently.

## 📌 Phase 2 Branch Progress
* **OOP Refactor:** Replaced the plain transaction list with dedicated `Transaction`, `Income`, and `Expense` classes plus an `ExpenseTracker` class encapsulating income/expense calculations and totals.
* **Budget Limits:** Introduced a `Budget` class and category-based monthly spending limits — expenses that would exceed a category's cap are now rejected with a clear console message instead of being silently accepted.
  * *Note: limits are currently hardcoded at startup — a console interface for creating, viewing, and editing budgets hasn't been built yet and is planned for an upcoming phase.*
* **Budget Manager:** Extracted a dedicated `BudgetManager` class to own budget creation and validation, decoupling that responsibility from `ExpenseTracker`.
* **Precise Money Handling:** Reworked amounts to be stored internally as integer kopecks (converted to/from display values), avoiding floating-point rounding errors in totals and budget checks.
* **CLI Package:** Extracted a `cli/` package (`output.py` with an `Outer` formatter, `input.py` for validated user input) replacing the earlier ad-hoc `color_string()` helper.
* **Structured Logging:** Migrated error logging from plain file writes to Python's built-in `logging` module via a dedicated `logger` package.
* **Testing Setup:** Added `pytest` to the project and wrote the first test (`tests/test_logger.py`), covering logger configuration ahead of the fuller transaction test suite added in Phase 3.

## 📌 Phase 3 Branch Progress
* **Package Restructure:** Consolidated `Transaction.py`, `tracker.py`, `budget.py`, `budget_manager.py`, and `money.py` into a single `expense_tracker/` package (`models.py`, `tracker.py`, `constants.py`) with a clean public API exposed via `expense_tracker/__init__.py`.
* **Automated Testing:** Added `tests/test_transactions.py` with pytest cases covering income/expense creation, kopecks conversion, and transaction arithmetic (`__add__`/`__radd__`, built-in `sum()`).
* **Continuous Integration:** Configured a GitHub Actions workflow (`.github/workflows/ci.yml`) that checks out the repo, sets up Python 3.10, installs dependencies, and runs the pytest suite on every push and pull request to `main`/`master`.

## 📌 Phase 4 Branch Progress
* **SQLite Persistence:** Replaced `transactions.json` with a SQLite database — `database.py` (`init_db()` running `init.sql`'s DDL, connection handling with `.env`-driven `DB_NAME`) and a root-level `models.py` as the plain DB-access module (`create_user`, `add_transaction`, `get_all_transactions`, `set_budget`, `get_categories`, `delete_transaction`, `check_budget_status`, etc. — no business logic, just CRUD).
* **Layered Architecture:** `expense_tracker/` owns all business logic on top of that storage — `models.py` (`Transaction`/`Income`/`Expense`/`Budget`, money kept as integer kopecks internally) and `tracker.py` (`ExpenseTracker`/`BudgetManager`). Every state-changing method (`add_transaction`, `remove_transaction`, `set_budget`) persists itself by calling straight into the root `models.py` DB-access module; reads (balance, category totals, budget status) are computed in-memory from what `ExpenseTracker.from_db()` already loaded. `main.py` drives one `ExpenseTracker` instance per session instead of touching the database directly.
* **User Login:** Added a `users` table with hashed passwords (PBKDF2-HMAC-SHA256, stdlib only, no new dependency) — `main.py` now prompts for email/password at startup instead of running as a single implicit user.
* **Category Selection Menu:** Income/expense input picks a category from a numbered list instead of free-text entry. Categories live only in the `budgets` table (`transaction_type` column + nullable `monthly_limit` for income) — `create_user()` seeds a starter set once; there is no parallel Python category list.
* **Case-Insensitive Categories:** `"Food"` and `"food"` are treated as the same category — normalized to lowercase at write time and compared with `LOWER(...)` at query time.
* **Database Error Handling:** All database access goes through a shared `db_connection()` context manager (`database.py`) that logs and re-raises `sqlite3.Error` (originally) / `psycopg.Error` (after the PostgreSQL migration below); `main.py` catches these around startup, login, and each menu command so a database problem shows a message instead of crashing the program.
* **Configurable via `.env`:** Database connection settings and seed login credentials are read from `.env` (template in `.env.example`, whose placeholder values deliberately don't match the real `.env`) instead of being hardcoded.
* **Demo Data Script:** `seed.py` resets the database and inserts a demo user, 5 transactions across 3 categories, and 2 budgets, then prints a transactions/balance/category/budget-status report.
* **Test Suite Overhaul:** `tests/test_tracker.py`/`tests/test_transactions.py` (the JSON-era OOP tests) were replaced by `tests/test_expense_tracker.py` (same classes, now DB-backed), alongside new `tests/test_database.py`, `tests/test_models.py`, and `tests/test_main_db.py`. `tests/conftest.py`'s `temp_db` fixture gives every test its own throwaway database instead of touching the real one.
* **PostgreSQL Migration (Homework 30):** `database.py`/root `models.py`/`init.sql` moved from SQLite to PostgreSQL via `psycopg` — same four tables, same columns, same constraints (only `INTEGER PRIMARY KEY AUTOINCREMENT` became `SERIAL PRIMARY KEY`, since Postgres has no `AUTOINCREMENT` keyword). `get_connection()`/`db_connection()` now take an optional `dbname` (server-side database name) instead of a SQLite file path, and `init_db()` creates that database on the server if it doesn't exist yet before running the DDL. `seed.py`'s reset is now `database.drop_all_tables()` + `init_db()` instead of deleting a file. `tests/conftest.py`'s `temp_db` fixture creates and drops a real, randomly-named PostgreSQL database per test for isolation. CI (`.github/workflows/ci.yml`) now runs a `postgres:16` service container alongside the test job. The standalone scripts this was built from (Homework 30's own Task 2-9 exercises) still live, unchanged, in `postgres/`.

## 🛠 Tech Stack (Evolutionary)
* **Language:** Python
* **Backend:** Django, Django REST Framework (upcoming)
* **Database:** PostgreSQL (implemented, Phase 4-5; migrated from the earlier SQLite implementation)
* **Testing:** Pytest
* **CI/CD:** GitHub Actions

---
*Built with precision and scalability in mind.*