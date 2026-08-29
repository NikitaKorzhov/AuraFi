from __future__ import annotations

from money import to_kopecks, to_display


class Transaction:

    def __init__(self, amount: float | int, category: str):
        self.amount_kopecks = to_kopecks(amount)
        self.category = category

    @property
    def amount(self) -> float | int:
        return to_display(self.amount_kopecks)

    @amount.setter
    def amount(self, value: float | int):
        self.amount_kopecks = to_kopecks(value)

    @classmethod
    def _from_kopecks(cls, amount_kopecks: int, category: str):
        """Rebuilds a transaction from an already-converted kopecks value (no re-conversion)."""
        obj = cls.__new__(cls)
        obj.amount_kopecks = amount_kopecks
        obj.category = category
        return obj

    @classmethod
    def from_data(cls, data: dict):
        """Rebuilds a transaction from stored data (amount already in kopecks)."""
        if data["type"] == "income":
            return Income._from_kopecks(data["amount"], data["category"])
        elif data["type"] == "expense":
            return Expense._from_kopecks(data["amount"], data["category"])
        raise ValueError(f"Unknown transaction type: {data['type']}")

    @classmethod
    def from_input(cls, data: dict):
        """Builds a transaction from raw user input (amount in hryvnia, needs conversion)."""
        if data["type"] == "income":
            return Income(data["amount"], data["category"])
        elif data["type"] == "expense":
            return Expense(data["amount"], data["category"])
        raise ValueError(f"Unknown transaction type: {data['type']}")

    def to_dict(self) -> dict:
        return {
            "amount": self.amount_kopecks,  # stored as kopecks (int), e.g. 251.7 -> 25170
            "type": self.type_name,  # Uses the subclass's property
            "category": self.category,
        }

    # Base addition method (each subclass implements its own effect on the balance)
    def __add__(self, other):
        if isinstance(other, Transaction):
            return self.signed_amount + other.signed_amount
        elif isinstance(other, (int, float)):
            return self.signed_amount + other
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)


class Income(Transaction):
    type_name = "income"

    @property
    def signed_amount(self) -> int:
        return self.amount_kopecks  # Income is always positive (kopecks)


class Expense(Transaction):
    type_name = "expense"

    @property
    def signed_amount(self) -> int:
        return -self.amount_kopecks  # Expense is always negative (kopecks)
