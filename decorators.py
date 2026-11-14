from __future__ import annotations

import functools
import inspect
from datetime import datetime

from logger import get_logger

log = get_logger(__name__)


def log_transaction(func):
    """Logs a financial-state-changing call: method name, its arguments
    (without `self`) and a timestamp. INFO level, via the project's own
    `logger` module — reuses the same app.log/format every other module
    already logs through, instead of a second `logging.basicConfig`.

    Used on: ExpenseTracker.add_transaction, ExpenseTracker.remove_transaction,
    BudgetManager.set_budget.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%H:%M:%S")
        call_args = args[1:]  # drop `self`
        result = func(*args, **kwargs)
        log.info(f"{func.__name__}: args={call_args}, kwargs={kwargs}, time={timestamp}")
        return result

    return wrapper


def validate_amount(func):
    """Validates the `amount` argument: must be int/float (not bool) and > 0.

    Logs WARNING and raises ValueError on failure, rather than returning None —
    this is applied to `Transaction.__init__`, where returning None would just
    hand back a half-built object with no attributes set. Raising ValueError
    instead keeps rejection on the same path the app already handles: budget
    overruns (`BudgetManager.validate_expense`) raise the same exception, and
    `main.add_transaction_entry()` already catches `ValueError` around
    transaction creation and shows it as a red error message.

    Used on: Transaction.__init__ (shared by Income and Expense).
    """
    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind_partial(*args, **kwargs)
        amount = bound.arguments.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            log.warning(f"validate_amount: amount must be a number > 0, got: {amount!r}")
            raise ValueError(f"Amount must be a positive number, got: {amount!r}")
        return func(*args, **kwargs)

    return wrapper


def currency_aware(base_currency: str = "UAH"):
    """STUB — real currency conversion lands in Lesson 25 (HTTP + requests,
    exchange-rate API).

    Future logic: fetch the current exchange rate, convert a foreign-currency
    transaction into `base_currency`, and keep both the original and converted
    amounts. For now it only logs a DEBUG note (silent at the project's
    default INFO level — see logger/config.py) and calls through unchanged.

    Used on: ExpenseTracker.add_transaction.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log.debug(
                f"[currency_aware] Conversion not implemented yet. "
                f"Base currency: {base_currency}"
            )
            # TODO (Lesson 25): fetch the rate via requests.get(EXCHANGE_API_URL)
            # TODO (Lesson 25): convert the amount if currency != base_currency
            return func(*args, **kwargs)

        return wrapper

    return decorator
