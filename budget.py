from Transaction import Transaction

class Budget:
    def __init__(self,category,monthly_limit):
        self.category = category
        self.monthly_limit = monthly_limit

    def check_limit(self,transactions:list)->bool:
        total_spent = sum(
            tx.amount
            for tx in transactions
            if isinstance(tx, Transaction) and tx.category.lower() == self.category
        )
        return total_spent > self.monthly_limit