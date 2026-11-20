from __future__ import annotations

from logger import get_logger
from cli.output import Outer
from cli.input import input_transaction1

log = get_logger(__name__)


def input_transaction(transaction_type="", categories: dict | None = None):
    """Gathers amount+category for a new transaction. `categories` is the
    {category: monthly_limit} dict to build the selection menu from — callers
    (main.py) source it from the database via models.get_categories(), which
    is the only place category data lives."""
    transaction = {
        "amount": float,
        "category": categories or {},
    }
    transaction = input_transaction1(transaction)

    if not transaction:
        log.warning("Transaction input canceled by user")
        Outer.append_yellow("Transaction input canceled.").print()
        return None

    if transaction_type in ["income", "expense"]:
        transaction["type"] = transaction_type
    return transaction
