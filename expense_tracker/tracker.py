from __future__ import annotations

import models as db
from decorators import currency_aware, log_transaction
from expense_tracker.models import Budget, Expense, Income, Transaction, to_display


class ExpenseTracker:
    """In-memory view of one user's transactions. All the actual logic (budget
    checks, totals, category breakdowns) happens here — `db` (the root
    `models.py` module) is only ever called to persist a state change, never
    consulted for business decisions."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.transactions: list[Transaction] = []
        self.budget_manager = BudgetManager(user_id)

    @classmethod
    def from_db(cls, user_id: int) -> "ExpenseTracker":
        """Loads the tracker's full state (transactions + budgets/categories)
        from the database for `user_id`."""
        tracker = cls(user_id)
        tracker.transactions = [Transaction.from_row(row) for row in db.get_all_transactions(user_id)]
        tracker.budget_manager.load()
        return tracker

    def set_budget(self, category: str, transaction_type: str, monthly_limit: float | None = None):
        self.budget_manager.set_budget(category, transaction_type, monthly_limit)

    def get_categories(self, transaction_type: str) -> dict:
        return self.budget_manager.get_categories(transaction_type)

    def get_budget_limits(self):
        return self.budget_manager.get_limits_data(self.transactions)

    def get_expenses_by_category(self, category: str) -> list[Expense]:
        """Finds expenses in the overall transaction list by category"""
        category = category.lower()
        return [
            t
            for t in self.transactions
            if isinstance(t, Expense) and t.category.lower() == category
        ]

    @log_transaction
    @currency_aware()
    def add_transaction(self, transaction: Transaction):
        if not isinstance(transaction, Transaction):
            raise TypeError("Transaction must be of type Transaction.")
        if isinstance(transaction, Expense):
            self.budget_manager.validate_expense(transaction, self.transactions)

        # Persist first so the DB-assigned id is available on the in-memory object too.
        transaction.id = db.add_transaction(
            self.user_id,
            transaction.amount,
            transaction.type_name,
            transaction.category,
            transaction.description,
            date=transaction.date,
        )
        self.transactions.append(transaction)

    @log_transaction
    def remove_transaction(self, index: int):
        """Removes a transaction by its number (index).

        Accepts the user-facing number (starting from 1).
        """
        real_index = index - 1

        if 0 <= real_index < len(self.transactions):
            removed = self.transactions.pop(real_index)
            db.delete_transaction(removed.id)
            return removed
        else:
            raise IndexError("❌ No transaction with this number exists.")

    def calc_balance(self) -> float | int:
        return to_display(sum(self.transactions))

    def calc_income(self) -> float | int:
        return to_display(sum(x.amount_kopecks for x in self.transactions if isinstance(x, Income)))

    def calc_expense(self) -> float | int:
        return to_display(sum(x.amount_kopecks for x in self.transactions if isinstance(x, Expense)))

    def __str__(self) -> str:
        """Returns a formatted text table of transactions with their numbers."""
        if not self.transactions:
            return "📭 List is empty."

        lines = [f"{'#':<4} | {'Type':<8} | {'Category':<15} | {'Amount':<10}"]
        lines.append("-" * 45)

        for i, tx in enumerate(self.transactions, start=1):
            tx_type = "Income" if tx.type_name == "income" else "Expense"
            lines.append(f"{i:<4} | {tx_type:<8} | {tx.category:<15} | {tx.amount:<10}")

        return "\n".join(lines)


class BudgetManager:
    """Owns the user's category list (both expense budgets and income
    categories). `set_budget` is the one state-change entry point — it updates
    the in-memory dict and persists the same change via `db.set_budget`.

    Keyed by (category, transaction_type), not category alone — an income and
    an expense category can share the same name (e.g. both default category
    lists include "other"), and a plain string key would let one overwrite
    the other in this dict even though the database keeps them as distinct
    rows (see `categories`/`budgets` in init.sql)."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.budgets: dict[tuple[str, str], Budget] = {}

    def load(self):
        """Loads the full category list (both transaction types) from the database."""
        self.budgets = {}
        for transaction_type in ("expense", "income"):
            for category, limit in db.get_categories(self.user_id, transaction_type).items():
                self.budgets[(category, transaction_type)] = Budget(category, transaction_type, limit)

    @log_transaction
    def set_budget(self, category: str, transaction_type: str, monthly_limit: float | None = None):
        category = category.lower()
        self.budgets[(category, transaction_type)] = Budget(category, transaction_type, monthly_limit)
        db.set_budget(self.user_id, category, transaction_type, monthly_limit)

    def get_categories(self, transaction_type: str) -> dict:
        """{category: monthly_limit} for every category of `transaction_type` —
        what the category-selection menu is built from."""
        return {
            budget.category: budget.monthly_limit
            for budget in self.budgets.values()
            if budget.transaction_type == transaction_type
        }

    def validate_expense(self, transaction: Expense, current_transactions: list[Transaction]):
        category = transaction.category.lower()
        budget = self.budgets.get((category, "expense"))
        if budget is not None:
            all_transactions = current_transactions + [transaction]
            is_exceeded, total_spent = budget.check_limit(all_transactions)
            if is_exceeded:
                raise ValueError(
                    f"⚠️ Limit exceeded! Category '{transaction.category}' "
                    f"has a limit of {budget.monthly_limit}, but expenses would become {total_spent}"
                )

    def get_limits_data(self, current_transactions: list[Transaction]):
        return [
            (
                budget.category,
                to_display(sum(
                    t.amount_kopecks
                    for t in current_transactions
                    if isinstance(t, Expense) and t.category.lower() == budget.category
                )),
                budget.monthly_limit,
            )
            for budget in self.budgets.values()
            if budget.transaction_type == "expense"
        ]
