from __future__ import annotations

from budget import Budget
from Transaction import Expense, Transaction
from money import to_display

class BudgetManager:
    def __init__(self):
        self.budgets: dict[str, Budget] = {}

    def set_budget(self, category: str, limit: float | int):
        category = category.lower()
        self.budgets[category] = Budget(category, limit)

    def validate_expense(self, transaction: Expense, current_transactions: list[Transaction]):
        category = transaction.category.lower()
        if category in self.budgets:
            budget = self.budgets[category]
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
                category,
                to_display(sum(
                    t.amount_kopecks
                    for t in current_transactions
                    if isinstance(t, Expense) and t.category.lower() == category
                )),
                budget.monthly_limit,
            )
            for category, budget in self.budgets.items()
        ]