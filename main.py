from __future__ import annotations

import csv
import getpass
import json as json_module
import sys
from datetime import date as date_cls
from pathlib import Path

import psycopg
from sqlalchemy.exc import SQLAlchemyError

from cli_commands import build_parser
from config import get_settings
from database import init_db
from expense_tracker import ExpenseTracker, Income, Expense
from expense_tracker.cli import input_transaction
from expense_tracker.models import User
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
    Outer.append_purple(f"\n{tracker.spending_report()}").print()


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
        except SQLAlchemyError as e:
            log.error(f"Database error during login: {e}")
            Outer.append_red(f"Database error, please try again later: {e}").print()
            continue

        if user_id is not None:
            user = User(username=username, email=email)
            log.info(f"User {user.display()} logged in successfully")
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
    except (SQLAlchemyError, psycopg.Error) as e:
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
    except SQLAlchemyError as e:
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
        except SQLAlchemyError as e:
            log.error(f"Database error while processing command '{command}': {e}")
            Outer.append_red(f"Database error, please try again later: {e}").print()


def export_transactions(transactions: list, fmt: str, export_dir: str) -> None:
    """Homework 23: writes `transactions` out as CSV or JSON under `export_dir`
    (created if missing). `.value` is used explicitly for transaction_type —
    a bare `str(TransactionType.INCOME)` prints 'TransactionType.INCOME', not
    'income' (verified); every serializer here must get the plain value."""
    out_dir = Path(export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"transactions.{fmt}"

    if fmt == "csv":
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "type", "category", "amount", "description"])
            for t in transactions:
                writer.writerow([t.id, t.date, t.type_name.value, t.category, t.amount, t.description])
    else:
        data = [
            {
                "id": t.id,
                "date": t.date,
                "type": t.type_name.value,
                "category": t.category,
                "amount": t.amount,
                "description": t.description,
            }
            for t in transactions
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            json_module.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📤 Експортовано {len(transactions)} транзакцій у {out_path}")


def dispatch_command(args, tracker: ExpenseTracker, settings: dict) -> None:
    """The actual command logic, separated from `run_cli()`'s argv-parsing and
    `init_db()`/`ExpenseTracker.from_db()` bootstrapping below so it can be
    unit-tested directly (build `args` via `build_parser().parse_args([...])`,
    `tracker` via the `temp_db` fixture) without touching the real database."""
    currency = settings["base_currency"]

    if args.command == "add":
        tx_class = Income if args.transaction_type == "income" else Expense
        date = args.date or date_cls.today().isoformat()
        transaction = tx_class(args.amount, args.category, date=date, description=args.desc)
        if args.dry_run:
            print(f"[DRY RUN] Додано б: {transaction.formatted()} — зміни не збережено")
            return
        try:
            tracker.add_transaction(transaction)
        except ValueError as e:
            print(f"❌ {e}")
            return
        print(f"✅ {transaction.formatted()} додано (id={transaction.id})")

    elif args.command == "list":
        transactions = tracker.transactions
        if args.transaction_type:
            transactions = [t for t in transactions if t.type_name == args.transaction_type]
        if args.category:
            transactions = [t for t in transactions if t.category.lower() == args.category.lower()]
        if args.month:
            transactions = [t for t in transactions if (t.date or "").startswith(args.month)]

        if not transactions:
            print("📋 Транзакцій не знайдено")
        for t in transactions:
            print(f"[{t.id}] {t.formatted()}")

    elif args.command == "balance":
        print(f"💰 Баланс: {tracker.calc_balance():.2f} {currency}")

    elif args.command == "report":
        month = args.month or date_cls.today().strftime("%Y-%m")
        monthly = [t for t in tracker.transactions if (t.date or "").startswith(month)]
        income_total = sum((t.amount for t in monthly if not t.is_expense()), 0.0)
        expense_total = sum((t.amount for t in monthly if t.is_expense()), 0.0)
        print(f"📊 Звіт за {month}")
        print(f"Доходи:  +{income_total:.2f} {currency}")
        print(f"Витрати: -{expense_total:.2f} {currency}")
        print(f"Баланс:   {income_total - expense_total:.2f} {currency}")

    elif args.command == "delete":
        if args.dry_run:
            print(f"[DRY RUN] Видалено б транзакцію #{args.id} — зміни не збережено")
            return
        for i, t in enumerate(tracker.transactions, start=1):
            if t.id == args.id:
                tracker.remove_transaction(i)
                print(f"🗑️  Транзакцію #{args.id} видалено")
                return
        print(f"🗑️  Транзакцію #{args.id} не знайдено")

    elif args.command == "budget":
        if args.budget_command == "set":
            if args.dry_run:
                print(
                    f"[DRY RUN] Встановлено б ліміт для '{args.category}': "
                    f"{args.limit} {currency} — зміни не збережено"
                )
                return
            tracker.set_budget(args.category, "expense", args.limit)
            print(f"📌 Ліміт для '{args.category}': {args.limit} {currency}")

        elif args.budget_command == "show":
            budgets = [b for b in tracker.budget_manager.budgets.values() if b.transaction_type == "expense"]
            if not budgets:
                print("📊 Бюджетів не встановлено")
            for budget in budgets:
                pct = budget.utilization_pct(tracker.transactions)
                remaining = budget.remaining(tracker.transactions)
                warning = " ⚠️" if pct >= settings["warn_budget_pct"] else ""
                print(f"• {budget.category}: {pct}% використано, залишок {remaining} {currency}{warning}")

    elif args.command == "export":
        export_transactions(tracker.transactions, args.format, settings["export_dir"])


def run_cli() -> None:
    """Homework 23: the one-shot CLI (`python main.py add income --amount 5000
    --category Salary`) — an alternative to `main()`'s interactive menu above,
    built on the exact same ExpenseTracker/Transaction/Budget methods (nothing
    here re-implements business logic that already exists)."""
    settings = get_settings()
    args = build_parser().parse_args()
    init_db()
    tracker = ExpenseTracker.from_db(args.user_id)
    dispatch_command(args, tracker, settings)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli()
    else:
        main()
