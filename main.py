from __future__ import annotations

import getpass
import sqlite3

from database import init_db
from expense_tracker import ExpenseTracker, Income, Expense
from expense_tracker.cli import input_transaction
from models import authenticate_user, get_username_by_email
from logger import get_logger
from cli.output import Outer
from cli.input import input_index_to_delete

log = get_logger(__name__)

command_dict = {1: "input income", 2: "input expense", 3: "show all transactions", 4: "delete transaction", 5: "exit"}


def show_all_transactions(tracker: ExpenseTracker):
    if not tracker.transactions:
        Outer.append_orange("No transactions found.").print()
    else:
        Outer.append_purple(f"{tracker}").print()


def show_all_transactions_with_info(tracker: ExpenseTracker):
    if not tracker.transactions:
        Outer.append_orange("No transactions found.").print()
        return

    budget_line = "\n".join(
        f"• {cat}: {spent} / {limit} грн"
        for cat, spent, limit in tracker.get_budget_limits()
    )

    Outer.append_purple(f"{tracker}").print()
    Outer.append_yellow(
        f"Income sum: {tracker.calc_income()}, Expense sum: {tracker.calc_expense()}, total:{tracker.calc_balance()}"
    ).print()
    Outer.append_blue(f"{budget_line}").print()


def add_transaction_entry(tracker: ExpenseTracker, transaction_type: str):
    categories = tracker.get_categories(transaction_type)
    transaction = input_transaction(transaction_type, categories)
    if transaction is None:
        return

    tx_class = Income if transaction_type == "income" else Expense
    try:
        tracker.add_transaction(tx_class(transaction["amount"], transaction["category"]))
    except ValueError as e:
        log.error(f"Budget limit exceeded: {e}")
        Outer.append_red(f"Error: {e}").print()
        return

    Outer.append_green(f"{transaction_type} added successfully! ").append_yellow(
        f"{transaction}"
    ).new_line().new_line().append_blue("See transaction list below").print()
    show_all_transactions(tracker)


def delete_transaction_entry(tracker: ExpenseTracker):
    if not tracker.transactions:
        Outer.append_orange("No transactions to delete.").print()
        return

    show_all_transactions(tracker)

    idx = input_index_to_delete(
        Outer.append_blue("Enter index to delete (or 'q'): "),
        f"Invalid index. Please enter a number between 1 and {len(tracker.transactions)}.",
    )

    if idx is not None:
        try:
            removed = tracker.remove_transaction(idx)
        except IndexError as e:
            log.error(f"Index {idx} out of range (1-{len(tracker.transactions)}) for deletion")
            Outer.append_red(f"Error: Index out of range 1-{len(tracker.transactions)}.").print()
            return

        Outer.append_orange(f"Transaction {removed.category} — {removed.amount} ({removed.type_name}) deleted.").print()
        Outer.append_blue("See transaction list below").print()
        show_all_transactions(tracker)


def login() -> int | None:
    """Prompts for email/password and authenticates against the users table
    (populated e.g. by seed.py). Returns the user id on success, None if the
    user cancels with 'q'."""
    Outer.append_blue("=== Login ===").print()
    while True:
        email = input("Email (or 'q' to cancel): ").strip()
        if email.lower() == "q":
            return None

        password = getpass.getpass("Password: ")
        try:
            user_id = authenticate_user(email, password)
            username = get_username_by_email(email)
        except sqlite3.Error as e:
            log.error(f"Database error during login: {e}")
            Outer.append_red(f"Database error, please try again later: {e}").print()
            continue

        if user_id is not None:
            log.info(f"User '{username}' ({email}) logged in successfully")
            return user_id

        if username is not None:
            log.error(f"Failed login attempt for user '{username}' ({email}): wrong password")
        else:
            log.error(f"Failed login attempt for unknown email {email}")
        Outer.append_red("Invalid email or password. Try again.").print()


def main():
    log.info("Program starts")
    try:
        init_db()
    except sqlite3.Error as e:
        log.error(f"Failed to initialize database: {e}")
        Outer.append_red(f"Could not initialize the database: {e}").print()
        return

    user_id = login()
    if user_id is None:
        log.info("Login canceled, program ended")
        Outer.append_orange("Login canceled. Exiting.").print()
        return

    try:
        tracker = ExpenseTracker.from_db(user_id)
    except sqlite3.Error as e:
        log.error(f"Database error while loading tracker: {e}")
        Outer.append_red(f"Database error, please try again later: {e}").print()
        return

    while True:
        Outer.append_orange(f"Command list: {command_dict}").print()
        command = input(f"{Outer.append_blue('Input your command number: ')} ").strip()

        try:
            if command == "5":
                log.info("Program ended")
                Outer.append_green("Thank you for using this program").print()
                break
            elif command == "1":
                add_transaction_entry(tracker, "income")
            elif command == "2":
                add_transaction_entry(tracker, "expense")
            elif command == "3":
                show_all_transactions_with_info(tracker)
            elif command == "4":
                delete_transaction_entry(tracker)
            else:
                log.error(f"Command with number {command} not exists")
                Outer.append_red("Unknown command. Please try again.").print()
        except sqlite3.Error as e:
            log.error(f"Database error while processing command '{command}': {e}")
            Outer.append_red(f"Database error, please try again later: {e}").print()


if __name__ == "__main__":
    main()
