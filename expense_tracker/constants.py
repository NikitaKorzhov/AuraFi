from enum import Enum  # або звичайний Enum, якщо версія Python нижча за 3.11

class TransactionCategory(Enum):
    SALARY = "Зарплата"
    FOOD = "Їжа"
    RENT = "Оренда"