from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from decorators import validate_amount


def to_kopecks(amount: float | int) -> int:
    """Converts a hryvnia amount (float|int) into kopecks (int) for storage/calculation."""
    return round(amount * 100)


def to_display(kopecks: int) -> float | int:
    """Converts kopecks (int) back into a hryvnia amount (int if whole, float otherwise)."""
    value = kopecks / 100
    whole = int(value)
    return whole if value == whole else round(value, 2)


class TransactionType(str, Enum):
    """A `str` subclass, not just a plain Enum: every existing `== "income"`
    comparison, DB write, and Postgres `CHECK` constraint already expects a
    bare string — this way a member *is* that string everywhere it's used,
    so none of them needed to change (verified: `TransactionType.INCOME ==
    "income"` and f-string interpolation both give back the plain value)."""

    INCOME = "income"
    EXPENSE = "expense"


@dataclass(init=False)
class Transaction:
    """In-memory domain object. The database (see root `models.py`) stores the
    amount as a plain hryvnia float — kopecks only exist on this side of the
    boundary, converted on the way in/out.

    `@dataclass(init=False)`: fields are declared for a real `__repr__`/`__eq__`
    (and to document the shape, same spirit as a Django model's fields later),
    but `__init__` stays hand-written — a dataclass-generated one can't also
    have an `amount` *property* of the same name (the property object gets
    mistaken for that field's default), and `amount` has to stay a property:
    callers pass hryvnia, storage is kopecks.
    """

    category: str
    id: int | None = None
    date: str | None = None
    description: str = ""
    amount_kopecks: int = 0

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
        if row["transaction_type"] == TransactionType.INCOME:
            return Income._from_kopecks(to_kopecks(row["amount"]), row["category"], **extra)
        elif row["transaction_type"] == TransactionType.EXPENSE:
            return Expense._from_kopecks(to_kopecks(row["amount"]), row["category"], **extra)
        raise ValueError(f"Unknown transaction type: {row['transaction_type']}")

    def is_expense(self) -> bool:
        return self.type_name == TransactionType.EXPENSE

    def formatted(self) -> str:
        """E.g. '+ 5000.00 UAH [Salary] 2026-11-20' or '- 350.00 UAH [Food] 2026-11-20'."""
        sign = "-" if self.is_expense() else "+"
        return f"{sign} {self.amount:.2f} UAH [{self.category}] {self.date}"

    # Base addition method (each subclass implements its own effect on the balance)
    def __add__(self, other):
        if isinstance(other, Transaction):
            return self.signed_amount + other.signed_amount
        elif isinstance(other, (int, float)):
            return self.signed_amount + other
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)


@dataclass(init=False)
class Income(Transaction):
    type_name = TransactionType.INCOME

    @property
    def signed_amount(self) -> int:
        return self.amount_kopecks  # Income is always positive (kopecks)


@dataclass(init=False)
class Expense(Transaction):
    type_name = TransactionType.EXPENSE

    @property
    def signed_amount(self) -> int:
        return -self.amount_kopecks  # Expense is always negative (kopecks)


@dataclass(init=False)
class Budget:
    category: str
    transaction_type: str
    monthly_limit_kopecks: int | None

    def __init__(self, category: str, transaction_type: str, monthly_limit: float | int | None):
        self.category = category
        self.transaction_type = transaction_type
        self.monthly_limit_kopecks = to_kopecks(monthly_limit) if monthly_limit is not None else None

    @property
    def monthly_limit(self) -> float | int | None:
        return to_display(self.monthly_limit_kopecks) if self.monthly_limit_kopecks is not None else None

    def _spent_kopecks(self, transactions: list) -> int:
        return sum(
            tx.amount_kopecks
            for tx in transactions
            if isinstance(tx, Expense) and tx.category.lower() == self.category
        )

    def check_limit(self, transactions: list) -> tuple[bool, float | int]:
        total_spent_kopecks = self._spent_kopecks(transactions)
        exceeded = self.monthly_limit_kopecks is not None and total_spent_kopecks > self.monthly_limit_kopecks
        return exceeded, to_display(total_spent_kopecks)

    def remaining(self, transactions: list) -> float | int | None:
        """How much of the monthly limit is left (can go negative if exceeded).
        None for a category with no limit (e.g. income)."""
        if self.monthly_limit_kopecks is None:
            return None
        return to_display(self.monthly_limit_kopecks - self._spent_kopecks(transactions))

    def is_exceeded(self, transactions: list) -> bool:
        exceeded, _ = self.check_limit(transactions)
        return exceeded

    def utilization_pct(self, transactions: list) -> float:
        """0.0-100.0+ — percentage of the limit already spent. 0.0 for a
        category with no limit (nothing to divide by)."""
        if not self.monthly_limit_kopecks:
            return 0.0
        return round(100 * self._spent_kopecks(transactions) / self.monthly_limit_kopecks, 1)


@dataclass
class User:
    """Lightweight carrier for the three fields `main.py`'s login flow already
    looks up separately (`authenticate_user`/`get_username_by_email`) — not
    persisted itself (the `users` table/root `models.py` stay the source of
    truth), just a convenience for passing them around as one value."""

    username: str
    email: str
    currency: str = "UAH"

    def display(self) -> str:
        return f"{self.username} <{self.email}>"
