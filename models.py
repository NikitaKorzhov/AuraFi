from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from datetime import date as date_cls

from database import db_connection

# Starter categories (hryvnia monthly budgets) seeded once into the `budgets`
# table when a user is created — the database is the only source read from
# after that point (via get_categories()), not these dicts.
DEFAULT_EXPENSE_CATEGORIES = {
    "food": 15000,
    "rent": 10000,
    "medicine": 5000,
    "transport": 3000,
    "entertainment": 2000,
    "subscriptions": 2000,
    "other": 5000,
}

# Income has no budget concept, so there's no limit to seed — None means
# "no monthly limit" (see init.sql: budgets.monthly_limit is nullable).
DEFAULT_INCOME_CATEGORIES = ["salary", "freelance", "gift", "other"]


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def _hash_password(password: str, salt: bytes | None = None) -> str:
    """PBKDF2-HMAC-SHA256 with a random salt (stdlib only, no extra dependency).
    Stored as 'salt_hex$digest_hex' in users.password_hash."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, _, _ = stored_hash.partition("$")
    salt = bytes.fromhex(salt_hex)
    return hmac.compare_digest(_hash_password(password, salt), stored_hash)


def create_user(username: str, email: str, password: str, seed_default_categories: bool = True) -> int:
    """Inserts a new user (password is hashed before storage) and returns its id.

    By default also seeds the starter category list (DEFAULT_EXPENSE_CATEGORIES /
    DEFAULT_INCOME_CATEGORIES) into `budgets`, once, atomically with user
    creation — so the category-selection menu always has something to show
    without main.py re-syncing a Python constant into the database on every
    startup. Pass seed_default_categories=False for a blank-slate user (e.g.
    in tests that set up their own categories)."""
    with db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, _hash_password(password)),
        )
        user_id = cur.lastrowid

        if seed_default_categories:
            for category, limit in DEFAULT_EXPENSE_CATEGORIES.items():
                conn.execute(
                    "INSERT INTO budgets (category, transaction_type, monthly_limit, user_id) "
                    "VALUES (?, 'expense', ?, ?)",
                    (category, limit, user_id),
                )
            for category in DEFAULT_INCOME_CATEGORIES:
                conn.execute(
                    "INSERT INTO budgets (category, transaction_type, monthly_limit, user_id) "
                    "VALUES (?, 'income', NULL, ?)",
                    (category, user_id),
                )

        conn.commit()
        return user_id


def authenticate_user(email: str, password: str) -> int | None:
    """Looks up the user by email and verifies the password against its stored
    hash. Returns the user id on success, None on no-match (unknown email or
    wrong password — both reported identically to the caller)."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()

    if row is None:
        return None

    user_id, password_hash = row
    return user_id if _verify_password(password, password_hash) else None


def get_username_by_email(email: str) -> str | None:
    """Looks up the username for `email` without checking a password — used to
    attribute a login attempt (successful or failed) to a username in logs."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE email = ?", (email,)
        ).fetchone()
    return row[0] if row else None


def add_transaction(
    user_id: int,
    amount: float,
    transaction_type: str,
    category: str,
    description: str,
    date: str | None = None,
) -> int:
    """Inserts a new transaction for `user_id` and returns its id.

    `date` defaults to today (ISO format) and only needs to be passed explicitly
    when backdating a transaction, e.g. when seeding demo data.
    """
    if transaction_type not in ("income", "expense"):
        raise ValueError(f"transaction_type must be 'income' or 'expense', got {transaction_type!r}")

    category = category.strip().lower()
    date = date or date_cls.today().isoformat()

    with db_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO transactions (amount, transaction_type, category, date, description, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (amount, transaction_type, category, date, description, user_id),
        )
        conn.commit()
        return cur.lastrowid


def get_all_transactions(user_id: int) -> list[dict]:
    """Returns every transaction belonging to `user_id`, oldest first."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, amount, transaction_type, category, date, description, user_id
            FROM transactions
            WHERE user_id = ?
            ORDER BY date, id
            """,
            (user_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def get_balance(user_id: int) -> float:
    """Returns income minus expenses for `user_id`."""
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return row[0] or 0.0


def get_expenses_by_category(user_id: int) -> list[dict]:
    """Returns total expenses per category for `user_id`, highest spend first.

    Grouped by LOWER(category) so 'Food' and 'food' are treated as the same
    category (defensive against any mixed-case rows written before categories
    were normalized at insert time)."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT LOWER(category) AS category, SUM(amount) AS total
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'expense'
            GROUP BY LOWER(category)
            ORDER BY total DESC
            """,
            (user_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def set_budget(user_id: int, category: str, transaction_type: str, monthly_limit: float | None = None) -> int:
    """Creates or updates (if one already exists for this user+category+type) the
    category/monthly-limit row, and returns its id. `monthly_limit=None` means
    no limit (the only sensible value for an income category).

    `category` is normalized to lowercase so budgets are matched case-insensitively
    against transaction categories (see add_transaction)."""
    if transaction_type not in ("income", "expense"):
        raise ValueError(f"transaction_type must be 'income' or 'expense', got {transaction_type!r}")

    category = category.strip().lower()
    with db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM budgets WHERE user_id = ? AND transaction_type = ? AND LOWER(category) = ?",
            (user_id, transaction_type, category),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE budgets SET monthly_limit = ? WHERE id = ?",
                (monthly_limit, existing[0]),
            )
            budget_id = existing[0]
        else:
            cur = conn.execute(
                "INSERT INTO budgets (category, transaction_type, monthly_limit, user_id) VALUES (?, ?, ?, ?)",
                (category, transaction_type, monthly_limit, user_id),
            )
            budget_id = cur.lastrowid

        conn.commit()
        return budget_id


def get_categories(user_id: int, transaction_type: str) -> dict:
    """Returns {category: monthly_limit} for every category of `transaction_type`
    the user has — this is what the category-selection menu is built from (the
    database is the only source; there is no parallel Python category list)."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id = ? AND transaction_type = ? ORDER BY category",
            (user_id, transaction_type),
        ).fetchall()
    return {category: limit for category, limit in rows}


def get_budget_limits(user_id: int) -> list[dict]:
    """Returns every budgeted category for `user_id` with its all-time expense total
    and monthly limit (unlike check_budget_status, this is not scoped to the current
    month) — used to display budget status and to enforce limits when adding an
    expense.

    Categories are compared case-insensitively (LOWER(...) on both sides of the
    JOIN), so a budget on 'Food' still matches a 'food' expense."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                LOWER(b.category) AS category,
                b.monthly_limit AS monthly_limit,
                COALESCE(SUM(t.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN transactions t
                ON LOWER(t.category) = LOWER(b.category)
                AND t.user_id = b.user_id
                AND t.transaction_type = 'expense'
            WHERE b.user_id = ? AND b.transaction_type = 'expense'
            GROUP BY LOWER(b.category)
            ORDER BY LOWER(b.category)
            """,
            (user_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def delete_transaction(transaction_id: int) -> bool:
    """Deletes a transaction by id. Returns True if a row was actually removed."""
    with db_connection() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        return cur.rowcount > 0


def check_budget_status(user_id: int) -> list[dict]:
    """Compares this month's actual expenses per category against the configured
    monthly budget for `user_id` (JOIN transactions + budgets), prints a warning
    for every category that is over its limit, and returns the full comparison.

    Categories are compared case-insensitively, same as get_budget_limits."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        month_prefix = date_cls.today().strftime("%Y-%m")
        rows = conn.execute(
            """
            SELECT
                LOWER(b.category) AS category,
                b.monthly_limit AS monthly_limit,
                COALESCE(SUM(t.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN transactions t
                ON LOWER(t.category) = LOWER(b.category)
                AND t.user_id = b.user_id
                AND t.transaction_type = 'expense'
                AND strftime('%Y-%m', t.date) = ?
            WHERE b.user_id = ? AND b.transaction_type = 'expense'
            GROUP BY LOWER(b.category)
            ORDER BY LOWER(b.category)
            """,
            (month_prefix, user_id),
        ).fetchall()

    statuses = []
    for row in rows:
        spent = row["spent"]
        limit = row["monthly_limit"]
        exceeded = spent > limit
        statuses.append(
            {
                "category": row["category"],
                "spent": spent,
                "monthly_limit": limit,
                "exceeded": exceeded,
            }
        )
        if exceeded:
            print(
                f"⚠️  Budget exceeded for '{row['category']}': "
                f"{spent:.2f} spent vs {limit:.2f} limit"
            )

    return statuses
