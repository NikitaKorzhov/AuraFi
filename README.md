# AuraFi

**AuraFi** is a scalable personal finance management platform that evolves from a lightweight Python CLI utility into a robust, full-stack web application. Designed with modern architecture in mind, it bridges the gap between fast local utility logging and comprehensive visual data analytics.

### 🌟 Key Capabilities
* **Flexible Tracking:** Seamlessly manage income and expenses across customizable categories.
* **Data Transparency:** Inspect transactions through structured data tables and clean state models.
* **Visual Insights:** Gain deep control over your budget via interactive financial dashboards.

## 🚀 Project Roadmap

* **Phase 1-3 (Core Python & Storage):** Building a solid foundation with a CLI interface, OOP architecture, and persistent local storage (JSON/CSV).
* **Phase 4-5 (Testing & Databases):** Implementing unit tests, currency conversion, and migrating data structures to relational databases (SQLite/PostgreSQL).
* **Phase 6-7 (Web & API):** Evolving into a full-stack web application with Django, dynamic dashboards, and REST API endpoints (DRF).
* **Phase 8 (Polish & Deploy):** Clean architecture, advanced analytics, and production deployment.

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

## 🛠 Tech Stack (Evolutionary)
* **Language:** Python
* **Backend:** Django, Django REST Framework (upcoming)
* **Database:** SQLite / PostgreSQL (upcoming)
* **Testing:** Pytest
* **CI/CD:** GitHub Actions

---
*Built with precision and scalability in mind.*