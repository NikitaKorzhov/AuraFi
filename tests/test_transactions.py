import pytest
import expense_tracker as tracker

@pytest.mark.parametrize("amount,category",[
    (500,"food"),
    (44.7,"drags")
])
def test_create_income(amount,category):
    income=tracker.Income(amount,category)
    assert income.type_name=="income" and income.amount==amount,f"Not correct type"

@pytest.mark.parametrize("amount,category",[
    (500,"food"),
    (44.7,"drags")
])
def test_kopeks(amount,category):
    income=tracker.Income(amount,category);
    assert income.amount_kopecks==amount*100,"Not valid to kopeks convertation"

@pytest.mark.parametrize("amount,category,didgit",[
    (500,"food",66),
    (44.7,"drags",89)
])
def test_add_transaction_to_didgit(amount,category,didgit):
    sum=100*(amount)+didgit
    income=tracker.Income(amount,category)
    assert income+didgit==sum and didgit+income==sum,"No corectb add operation "


@pytest.mark.parametrize("t1_class, amt1, t2_class, amt2, expected_kopecks", [
    (tracker.Income, 500, tracker.Income, 50, 55000),    # Дохід + Дохід
    (tracker.Expense, 100, tracker.Expense, 20, -12000), # Витрата + Витрата
    (tracker.Income, 500, tracker.Expense, 50, 45000),   # Дохід + Витрата
    (tracker.Expense, 50, tracker.Income, 500, 45000),   # Витрата + Дохід (перевірка __radd__)
])
def test_transaction_combinations(t1_class, amt1, t2_class, amt2, expected_kopecks):
    t1 = t1_class(amt1, "test")
    t2 = t2_class(amt2, "test")
    
    assert t1 + t2 == expected_kopecks, "Incorrect addition result for transaction combination"



def test_builtin_sum():
    transactions = [
        tracker.Income(100, "salary"),
        tracker.Income(50, "gift"),
        tracker.Expense(30, "food")
    ]
    # 10000 + 5000 - 3000 = 12000 копійок
    assert sum(transactions) == 12000, "Built-in sum() failed with transactions"