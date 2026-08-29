from Transaction import Expense

class Budget:
    def __init__(self,category,monthly_limit):
        self.category = category
        self.monthly_limit = monthly_limit

    def check_limit(self, transactions: list) -> tuple[bool, float]:
        total_spent = sum(
            tx.amount
            for tx in transactions
            if isinstance(tx, Expense) and tx.category.lower() == self.category
        )
        return total_spent > self.monthly_limit, total_spent