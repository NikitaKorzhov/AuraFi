"""Homework 23: argparse-based one-shot CLI — the alternative to main.py's
interactive menu (`python main.py add expense --amount 350 --category Food`
instead of running the program and navigating a numbered menu).

Not to be confused with the existing `cli/` package (generic terminal I/O:
`Outer`, `input_category`, etc.) or `expense_tracker/cli.py` (the interactive
menu's transaction-input helper) — this is the new argparse layer only.
"""

from __future__ import annotations

import argparse

from config import get_settings


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="aurafi",
        description=f"{settings['app_name']} — облік доходів і витрат",
        epilog="Приклад: python main.py add expense --amount 350 --category Food",
    )
    parser.add_argument(
        "--version", action="version", version=f"{settings['app_name']} v{settings['app_version']}"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=settings["cli_user_id"],
        help="ID користувача (за замовчуванням CLI_USER_ID з .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Лише показати, що було б зроблено, без запису у БД",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # --- add ---
    add_parser = subparsers.add_parser("add", help="Додати транзакцію")
    add_parser.add_argument("transaction_type", choices=["income", "expense"], help="Тип транзакції")
    add_parser.add_argument("--amount", type=float, required=True, help="Сума")
    add_parser.add_argument("--category", required=True, help="Категорія")
    add_parser.add_argument("--desc", default="", help="Опис (необов'язково)")
    add_parser.add_argument("--date", metavar="YYYY-MM-DD", help="Дата (за замовчуванням: сьогодні)")

    # --- list ---
    list_parser = subparsers.add_parser("list", help="Переглянути транзакції")
    list_parser.add_argument(
        "--type", dest="transaction_type", choices=["income", "expense"], help="Фільтр за типом"
    )
    list_parser.add_argument("--category", help="Фільтр за категорією")
    list_parser.add_argument("--month", metavar="YYYY-MM", help="Фільтр за місяцем")

    # --- balance ---
    subparsers.add_parser("balance", help="Показати поточний баланс")

    # --- report ---
    report_parser = subparsers.add_parser("report", help="Місячний звіт")
    report_parser.add_argument(
        "--month", metavar="YYYY-MM", help="Місяць звіту (за замовчуванням: поточний)"
    )

    # --- delete ---
    delete_parser = subparsers.add_parser("delete", help="Видалити транзакцію")
    delete_parser.add_argument("--id", type=int, required=True, help="ID транзакції")

    # --- budget ---
    budget_parser = subparsers.add_parser("budget", help="Керування бюджетом")
    budget_sub = budget_parser.add_subparsers(dest="budget_command", metavar="SUBCOMMAND")
    budget_sub.required = True

    budget_set = budget_sub.add_parser("set", help="Встановити ліміт")
    budget_set.add_argument("--category", required=True, help="Категорія")
    budget_set.add_argument("--limit", type=float, required=True, help="Місячний ліміт")

    budget_sub.add_parser("show", help="Переглянути бюджети та використання")

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Експортувати транзакції")
    export_parser.add_argument(
        "--format", choices=["csv", "json"], default="csv", help="Формат (за замовчуванням: csv)"
    )

    return parser
