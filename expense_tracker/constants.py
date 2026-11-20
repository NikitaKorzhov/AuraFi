from enum import Enum  # або звичайний Enum, якщо версія Python нижча за 3.11

class TransactionCategory(Enum):
    SALARY = "Зарплата"
    FOOD = "Їжа"
    RENT = "Оренда"


# Category -> monthly budget (hryvnia). Used to build the category selection
# menu when entering a transaction, and (for expenses) to seed BudgetManager
# limits in main().
EXPENSE_CATEGORIES = {
    "food": 15000,
    "rent": 10000,
    "medicine": 5000,
    "transport": 3000,
    "entertainment": 2000,
    "subscriptions": 2000,
    "other": 5000,
}

INCOME_CATEGORIES = {
    "salary": 50000,
    "freelance": 20000,
    "gift": 5000,
    "other": 5000,
}