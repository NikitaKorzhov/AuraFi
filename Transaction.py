class Transaction:

    def __init__(self, amount: int, category: str):
        self.amount = amount
        self.category = category

    @classmethod
    def from_data(cls, data: dict):
        # The factory decides which object to create
        if data["type"] == "income":
            return Income(data["amount"], data["category"])
        elif data["type"] == "expense":
            return Expense(data["amount"], data["category"])
        raise ValueError(f"Unknown transaction type: {data['type']}")

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
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
        return self.amount  # Income is always positive


class Expense(Transaction):
    type_name = "expense"

    @property
    def signed_amount(self) -> int:
        return -self.amount  # Expense is always negative