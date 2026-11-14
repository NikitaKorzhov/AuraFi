from __future__ import annotations

from decorators import validate_amount


def to_kopecks(amount: float | int) -> int:
    """Converts a hryvnia amount (float|int) into kopecks (int) for storage/calculation."""
    return round(amount * 100)


def to_display(kopecks: int) -> float | int:
    """Converts kopecks (int) back into a hryvnia amount (int if whole, float otherwise)."""
    value = kopecks / 100
    whole = int(value)
    return whole if value == whole else round(value, 2)


class Transaction:
    """In-memory domain object. The database (see root `models.py`) stores the
    amount as a plain hryvnia float — kopecks only exist on this side of the
    boundary, converted on the way in/out."""

    @validate_amount
    def __init__(self, amount: float | int, category: str, *, id: int | None = None,
                 date: str | None = None, description: str = ""):
        self.id = id
        self.amount_kopecks = to_kopecks(amount)
        self.category = category
        self.date = date
        self.description = description

    @property
    def amount(self) -> float | int:
        return to_display(self.amount_kopecks)

    @amount.setter
    def amount(self, value: float | int):
        self.amount_kopecks = to_kopecks(value)

    @classmethod
    def _from_kopecks(cls, amount_kopecks: int, category: str, **extra):
        """Rebuilds a transaction from an already-converted kopecks value (no re-conversion)."""
        obj = cls.__new__(cls)
        obj.amount_kopecks = amount_kopecks
        obj.category = category
        obj.id = extra.get("id")
        obj.date = extra.get("date")
        obj.description = extra.get("description", "")
        return obj

    @classmethod
    def from_row(cls, row: dict) -> "Transaction":
        """Rebuilds a Transaction from a DB row (`models.get_all_transactions()`'s
        dict shape — amount is a hryvnia float there, needs kopecks conversion)."""
        extra = {"id": row["id"], "date": row["date"], "description": row["description"]}
        if row["transaction_type"] == "income":
            return Income._from_kopecks(to_kopecks(row["amount"]), row["category"], **extra)
        elif row["transaction_type"] == "expense":
            return Expense._from_kopecks(to_kopecks(row["amount"]), row["category"], **extra)
        raise ValueError(f"Unknown transaction type: {row['transaction_type']}")

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


class Budget:
    def __init__(self, category: str, transaction_type: str, monthly_limit: float | int | None):
        self.category = category
        self.transaction_type = transaction_type
        self.monthly_limit_kopecks = to_kopecks(monthly_limit) if monthly_limit is not None else None

    @property
    def monthly_limit(self) -> float | int | None:
        return to_display(self.monthly_limit_kopecks) if self.monthly_limit_kopecks is not None else None

    def check_limit(self, transactions: list) -> tuple[bool, float | int]:
        total_spent_kopecks = sum(
            tx.amount_kopecks
            for tx in transactions
            if isinstance(tx, Expense) and tx.category.lower() == self.category
        )
        exceeded = self.monthly_limit_kopecks is not None and total_spent_kopecks > self.monthly_limit_kopecks
        return exceeded, to_display(total_spent_kopecks)
