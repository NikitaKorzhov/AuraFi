from Transaction import Expense, Income, Transaction
from budget_manager import BudgetManager

class ExpenseTracker:

    def __init__(self):
        self.transactions: list[Transaction] = []
        self.budget_manager: BudgetManager = BudgetManager()

    @classmethod
    def from_data(cls, data: list[dict]):
        tracker = cls()
        for item in data:
            tx = Transaction.from_data(item)
            tracker.add_transaction(tx)
        return tracker

    def set_budget(self, category: str, limit: float):
        self.budget_manager.set_budget(category, limit)

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

    def add_transaction(self, transaction: Transaction):
        if not isinstance(transaction, Transaction):
            raise TypeError("Transaction must be of type Transaction.")
        if isinstance(transaction, Expense):
           self.budget_manager.validate_expense(transaction, self.transactions)
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