from __future__ import annotations

from expense_tracker import ExpenseTracker
from expense_tracker.constants import EXPENSE_CATEGORIES
from expense_tracker.cli import (
    read_transactions,
    add_transaction,
    show_all_transactions_with_info,
    delete_transaction,
)
from logger import get_logger
from cli.output import Outer

log = get_logger(__name__)

command_dict = {1: "input income", 2: "input expense", 3: "show all transactions", 4: "delete transaction", 5: "exit"}


def main():
    log.info("Program starts")
    transactions = ExpenseTracker.from_data(read_transactions())
    for category, limit in EXPENSE_CATEGORIES.items():
        transactions.set_budget(category, limit)

    while True:
        Outer.append_orange(f"Command list: {command_dict}").print()
        command = input(f"{Outer.append_blue('Input your command number: ')} ").strip()

        if command == "5":
            log.info("Program ended")
            Outer.append_green("Thank you for using this program").print()
            break
        elif command == "1":
            add_transaction(transactions, "income")
        elif command == "2":
            add_transaction(transactions, "expense")
        elif command == "3":
            show_all_transactions_with_info(transactions)
        elif command == "4":
            delete_transaction(transactions)
        else:
            log.error(f"Command with number {command} not exists")
            Outer.append_red("Unknown command. Please try again.").print()


if __name__ == "__main__":
    main()
