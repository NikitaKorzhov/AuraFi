from __future__ import annotations

import json
import os

from expense_tracker.models import Transaction
from expense_tracker.tracker import ExpenseTracker
from logger import get_logger
from cli.output import Outer
from cli.input import input_transaction1, input_index_to_delete

log = get_logger(__name__)

# File storage
FILE_PATH = "transactions.json"  # File name to save transactions list


def write_transactions(transactions: list, file_path: str = FILE_PATH):
    """Function to write entire transactions into file

    :param transactions: list of transactions
    :type transactions: list
    :param file_path: path to the storage file
    :type file_path: str"""
    clean_data = []
    for item in transactions:
        cleaned_item = {
            k: (v.encode('utf-8', 'ignore').decode('utf-8') if isinstance(v, str) else v)
            for k, v in item.items()
        }
        clean_data.append(cleaned_item)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)


def read_transactions(file_path: str = FILE_PATH):
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
# --------------------------------------------------------------


def is_cancel_requested(cancellation_char: str):
    if cancellation_char == 'q':
        Outer.append_orange("Your action canceled").print()
        return True
    else:
        return False


def input_transaction(transaction_type=""):
    transaction = {
        "amount": float,
        "category": str,
    }
    transaction = input_transaction1(transaction)

    if not transaction:
        log.warning("Transaction input canceled by user")
        Outer.append_yellow("Transaction input canceled.").print()
        return None

    if transaction_type in ["income", "expense"]:
        transaction["type"] = transaction_type
    return transaction


# Transaction list and functions to operate with it from console


def add_transaction(tracker: ExpenseTracker, transaction_type: str):
    transaction = input_transaction(transaction_type)
    if transaction is not None:
        try:
            tracker.add_transaction(Transaction.from_input(transaction))
        except ValueError as e:
            log.error(f"Budget limit exceeded: {e}")
            Outer.append_red(f"Error: {e}").print()
            return
        out = Outer
        out.append_green(f"{transaction_type} added successfully! ").append_yellow(f"{transaction}").new_line().new_line().append_blue("See transaction list below").print()
        show_all_transactions(tracker)
        write_transactions(tracker.to_list())


def show_all_transactions(tracker: ExpenseTracker):
    if not tracker:
        Outer.append_orange("No transactions found.").print()
    else:
        Outer.append_purple(f"{tracker}").print()


def show_all_transactions_with_info(tracker: ExpenseTracker):
    if not tracker:
        Outer.append_orange("No transactions found.").print()
    else:
        transactions_info = Outer.append_yellow(
            f"Income sum: {tracker.calc_income()}, Expense sum: {tracker.calc_expense()}, total:{tracker.calc_balance()}"
        )
        budget_line = "\n".join(
            f"• {cat}: {spent} / {limit} грн"
            for cat, spent, limit in tracker.get_budget_limits()
        )
        Outer.append_purple(f"{tracker}").print()
        Outer.append_yellow(f"{transactions_info}").print()
        Outer.append_blue(f"{budget_line}").print()


def delete_transaction(tracker: ExpenseTracker):
    if not tracker:
        Outer.append_orange("No transactions to delete.").print()
    else:
        show_all_transactions(tracker)

        idx = input_index_to_delete(
            Outer.append_blue("Enter index to delete (or 'q'): "),
            f"Invalid index. Please enter a number between 1 and {len(tracker.transactions)}.",
        )

        if idx is not None:
            if 0 < idx <= len(tracker.transactions):
                removed = tracker.remove_transaction(idx)
                Outer.append_orange(f"Transaction {removed} deleted.").print()
                Outer.append_blue("See transaction list below").print()
                show_all_transactions(tracker)
                write_transactions(tracker.to_list())
            else:
                log.error(f"Index {idx} out of range (1-{len(tracker.transactions)}) for deletion")
                Outer.append_red(f"Error: Index out of range 1-{len(tracker.transactions)}.").print()
