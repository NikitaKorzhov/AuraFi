from budget import Budget
from Transaction import Expense, Income, Transaction


class ExpenseTracker:

    def __init__(self):
        self.transactions: list[Transaction] = []
        self.budgets: dict[str, Budget] = {}  # Key - category, value - Budget

    @classmethod
    def from_data(cls, data: list[dict]):
        tracker = cls()
        for item in data:
            tx = Transaction.from_data(item)
            tracker.addTransaction(tx)
        return tracker

    def set_budget(self, category: str, limit: float):
        self.budgets[category] = Budget(category, limit)

    def get_expenses_by_category(self, category: str) -> list[Expense]:
        """Finds expenses in the overall transaction list by category"""
        return [
            t
            for t in self.transactions
            if isinstance(t, Expense) and t.category == category
        ]

    def addTransaction(self, transaction: Transaction):
        # If this is an expense and a budget limit is set for this category
        if isinstance(transaction, Expense) and transaction.category in self.budgets:
            # Calculate how much has already been spent in this category
            current_spent = sum(
                t.amount
                for t in self.get_expenses_by_category(transaction.category)
            )

            budget = self.budgets[transaction.category]

            # Check whether the new expense would exceed the limit
            if current_spent + transaction.amount > budget.monthly_limit:
                raise ValueError(
                    f"⚠️ Limit exceeded! Category '{transaction.category}' "
                    f"has a limit of {budget.monthly_limit}, but expenses would become {current_spent + transaction.amount}"
                )

        self.transactions.append(transaction)

    def remove_transaction(self, index: int):
        """Removes a transaction by its number (index).

        Accepts the user-facing number (starting from 1).
        """
        real_index = index - 1

        if 0 <= real_index < len(self.transactions):
            removed = self.transactions.pop(real_index)
            print(
                f"🗑️ Transaction removed: {removed.category} — {removed.amount}"
                f" ({removed.type_name})"
            )
            return removed
        else:
            raise IndexError("❌ No transaction with this number exists.")

    def budget_count(self) -> int:
        return sum(self.transactions)

    def calc_income(self) -> int:
        return sum(x.amount for x in self.transactions if isinstance(x, Income))

    def calc_expense(self) -> int:
        return sum(x.amount for x in self.transactions if isinstance(x, Expense))

    def to_list(self) -> list[dict]:
        return [transaction.to_dict() for transaction in self.transactions]

    def __str__(self) -> str:
        """Returns a formatted text table of transactions with their numbers."""
        if not self.transactions:
            return "📭 List is empty5."

        # Build the table header
        lines = []
        lines.append(f"{'#':<4} | {'Type':<8} | {'Category':<15} | {'Amount':<10}")
        lines.append("-" * 45)

        # Walk through transactions, numbering them from 1
        for i, tx in enumerate(self.transactions, start=1):
            tx_type = "Income" if tx.type_name == "income" else "Expense"
            lines.append(f"{i:<4} | {tx_type:<8} | {tx.category:<15} | {tx.amount:<10}")

        return "\n".join(lines)