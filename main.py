from __future__ import annotations

import json
import os
from datetime import datetime

from tracker import ExpenseTracker
from Transaction import Transaction
from logger import get_logger
from cli.output import Outer




#Logger
log=get_logger(__name__)
#File storage
file_path = "transactions.json" #File name to save transactions list
def write_transactions(transactions:list):
    """Function to write entire transactions into file

    :param transactions: list of transactions
    :type transactions: list"""
    clean_data = []
    for item in transactions:
        cleaned_item = {
            k: (v.encode('utf-8', 'ignore').decode('utf-8') if isinstance(v, str) else v)
            for k, v in item.items()
        }
        clean_data.append(cleaned_item)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

def read_transactions():
    """Function to read entire transactions from file into list"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                log.error("Error while reading transactions file")
                return []
    else:
      return []
#--------------------------------------------------------------


def is_cancel_requested(cancellation_char:str):
    if cancellation_char == 'q':
        Outer.append_orange("Your action canceled").print()
        return True
    else:
        return False


def parse_amount(value: str) -> float | int:
    """Parses a user-entered amount as int (whole numbers) or float (with a decimal part).

    Rejects more than 2 digits after the decimal point (amounts are stored in kopecks).
    """
    normalized = value.replace(",", ".")
    if "." in normalized:
        decimal_part = normalized.split(".", 1)[1]
        if len(decimal_part) > 2:
            raise ValueError("Too many decimal places")
        return float(normalized)
    return int(normalized)


def get_input_with_cancel(prompt: str, data_type=str):
    """
    Function to cancel action by key 'q'
    and converting to required type (str by default).
    """
    while True:
        value = input(f"{Outer.append_blue(prompt)} ").strip()
        if is_cancel_requested(value):
            return None

        try:
            return data_type(value)
        except ValueError:
            if data_type is parse_amount:
                log.error("Invalid amount")
                Outer.append_red("Error: Please enter a valid number (e.g., 100 or 100.50).").print()
            elif data_type is int:
                log.error("Invalid amount")
                Outer.append_red("Error: Please enter a valid whole number (e.g., 10).").print()
            else:
                log.error('Invalid input for is_cancel_requested')
                Outer.append_red("Error: Invalid input format.").print()

def input_transaction(transaction_type=""):
    fields = [
        ("amount", parse_amount),
        ("category", str)
    ]

    transaction = {}

    if transaction_type in ["income", "expense"]:
        transaction["type"] = transaction_type
    else:
        fields.insert(1, ("type", str))

    for key, data_type in fields:
        prompt = f"Input {key} (or 'q' to cancel): "

        value = get_input_with_cancel(prompt, data_type)
        if value is None:
            return None

        transaction[key] = value

    return transaction


#Transaction list and functions to operate with it from console


def add_transaction(transaction_type:str):
    transaction = input_transaction(transaction_type)
    if transaction is not None:
        try:
            transactions.add_transaction(Transaction.from_input(transaction))
        except ValueError as e:
            log.error(f"Budget limit exceeded: {e}")
            Outer.append_red(f"Error: {e}").print()
            return
        out = Outer
        out.append_green(f"{transaction_type} added successfully! ").append_yellow(f"{transaction}").new_line().new_line().append_blue("See transaction list below").print()
        show_all_transactions()
        write_transactions(transactions.to_list())


def show_all_transactions():
    if not transactions:
        Outer.append_orange("No transactions found.").print()
    else:
         Outer.append_purple(f"{transactions}").print()

def show_all_transactions_with_info():
     if not transactions:
        Outer.append_orange("No transactions found.").print()
     else:
        transactions_Info=Outer.append_yellow(f"Income sum: {transactions.calc_income()}, Expense sum: {transactions.calc_expense()}, total:{transactions.calc_balance()}")
        budget_line = "\n".join(
            f"• {cat}: {spent} / {limit} грн"
            for cat, spent, limit in transactions.get_budget_limits()
        )
        Outer.append_purple(f"{transactions}").print()
        Outer.append_yellow(f"{transactions_Info}").print()
        Outer.append_blue(f"{budget_line}").print()

def delete_transaction():
    if not transactions:
        Outer.append_orange("No transactions to delete.").print()
    else:
        show_all_transactions()

        idx = get_input_with_cancel("Enter index to delete (or 'q'): ", int)

        if idx is not None:
            if 0 < idx <= len(transactions.transactions):
                removed = transactions.remove_transaction(idx)
                Outer.append_orange(f"Transaction {removed} deleted.").print()
                Outer.append_blue("See transaction list below").print()
                show_all_transactions()
                write_transactions(transactions.to_list())
            else:
                Outer.append_red("Error: Index out of range.").print()


command_dict={1:"input income", 2:"input expense",3:"show all transactions",4:"delete transaction",5:"exit"}



#While loop executing program
log.info("Program starts")
transactions=ExpenseTracker.from_data(read_transactions())
transactions.set_budget("Subscribes", 2000)
transactions.set_budget("food", 15000)
transactions.set_budget("medicine", 5000)
while True:
    Outer.append_orange(f"Command list: {command_dict}").print()
    command = input(f"{Outer.append_blue('Input your command number: ')} ").strip()

    if command == "5":
        log.info("Program ended")
        Outer.append_green("Thank you for using this program").print()
        break
    elif command == "1":
        add_transaction("income")
    elif command == "2":
        add_transaction("expense")
    elif command == "3":
        show_all_transactions_with_info()
    elif command == "4":
        delete_transaction()
    else:
        log.error(f"Command with number {command} not exists")
        Outer.append_red("Unknown command. Please try again.").print()