from __future__ import annotations

from Transaction import Expense
from money import to_kopecks, to_display

class Budget:
    def __init__(self, category, monthly_limit: float | int):
        self.category = category
        self.monthly_limit_kopecks = to_kopecks(monthly_limit)

    @property
    def monthly_limit(self) -> float | int:
        return to_display(self.monthly_limit_kopecks)

    def check_limit(self, transactions: list) -> tuple[bool, float | int]:
        total_spent_kopecks = sum(
            tx.amount_kopecks
            for tx in transactions
            if isinstance(tx, Expense) and tx.category.lower() == self.category
        )
        return total_spent_kopecks > self.monthly_limit_kopecks, to_display(total_spent_kopecks)
