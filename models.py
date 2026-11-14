from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import uuid as uuid_lib
from datetime import date as date_cls

from database import db_connection

# Starter categories (hryvnia monthly budgets) seeded once into `categories`
# (+ a matching `budgets` row per category) when a user is created — the
# database is the only source read from after that point (via
# get_categories()), not these dicts.
DEFAULT_EXPENSE_CATEGORIES = {
    "food": 15000,
    "rent": 10000,
    "medicine": 5000,
    "transport": 3000,
    "entertainment": 2000,
    "subscriptions": 2000,
    "other": 5000,
}

# Income has no budget concept, so these get a `categories` row only — no
# matching `budgets` row, which is what makes get_categories() report their
# limit as None (see get_categories()'s LEFT JOIN).
DEFAULT_INCOME_CATEGORIES = ["salary", "freelance", "gift", "other"]


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def _find_or_create_category(conn: sqlite3.Connection, name: str, transaction_type: str) -> str:
    """Finds the existing category row (matched case-insensitively) or creates
    one, and returns its uuid. `categories` is a shared catalog — not scoped to
    any one user — so this lookup is global. Does not commit — caller owns the
    transaction."""
    row = conn.execute(
        "SELECT uuid FROM categories WHERE transaction_type = ? AND LOWER(name) = ?",
        (transaction_type, name),
    ).fetchone()
    if row:
        return row[0]

    category_uuid = str(uuid_lib.uuid4())
    conn.execute(
        "INSERT INTO categories (uuid, name, transaction_type) VALUES (?, ?, ?)",
        (category_uuid, name, transaction_type),
    )
    return category_uuid


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
    DEFAULT_INCOME_CATEGORIES) into the shared `categories` catalog — reusing
    any of those categories that already exist (seeded by an earlier user) —
    plus a `budgets` row of this user's own for each expense category, so the
    category-selection menu always has something to show without main.py
    re-syncing a Python constant into the database on every startup. Pass
    seed_default_categories=False for a blank-slate user (e.g. in tests that
    set up their own categories)."""
    with db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, _hash_password(password)),
        )
        user_id = cur.lastrowid

        if seed_default_categories:
            for category, limit in DEFAULT_EXPENSE_CATEGORIES.items():
                category_uuid = _find_or_create_category(conn, category, "expense")
                conn.execute(
                    "INSERT INTO budgets (uuid, period_type, limit_amount, user_id, category_uuid) "
                    "VALUES (?, 'monthly', ?, ?, ?)",
                    (str(uuid_lib.uuid4()), limit, user_id, category_uuid),
                )
            for category in DEFAULT_INCOME_CATEGORIES:
                _find_or_create_category(conn, category, "income")

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
    """Inserts a new transaction for `user_id` and returns its id. `category` is
    a plain category name (not a uuid) — resolved to (or, if new, created as) a
    `categories` row, and it's that row's uuid that actually gets stored on the
    transaction (see `transactions.category_uuid`), never the name itself.

    `date` defaults to today (ISO format) and only needs to be passed explicitly
    when backdating a transaction, e.g. when seeding demo data.
    """
    if transaction_type not in ("income", "expense"):
        raise ValueError(f"transaction_type must be 'income' or 'expense', got {transaction_type!r}")

    category = category.strip().lower()
    date = date or date_cls.today().isoformat()

    with db_connection() as conn:
        category_uuid = _find_or_create_category(conn, category, transaction_type)
        cur = conn.execute(
            """
            INSERT INTO transactions (amount, transaction_type, category_uuid, date, description, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (amount, transaction_type, category_uuid, date, description, user_id),
        )
        conn.commit()
        return cur.lastrowid


def get_all_transactions(user_id: int) -> list[dict]:
    """Returns every transaction belonging to `user_id`, oldest first. `category`
    in each row is the category's name, resolved via `category_uuid` — callers
    never see the uuid, only the name (same shape as before this was a FK)."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT t.id, t.amount, t.transaction_type, c.name AS category, t.date, t.description, t.user_id
            FROM transactions t
            JOIN categories c ON c.uuid = t.category_uuid
            WHERE t.user_id = ?
            ORDER BY t.date, t.id
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

    Grouped by LOWER(category name) so 'Food' and 'food' are treated as the
    same category, even if they ended up as two different `categories` rows
    (defensive against any mixed-case category data, e.g. written directly
    rather than through add_transaction's normalization)."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT LOWER(c.name) AS category, SUM(t.amount) AS total
            FROM transactions t
            JOIN categories c ON c.uuid = t.category_uuid
            WHERE t.user_id = ? AND t.transaction_type = 'expense'
            GROUP BY LOWER(c.name)
            ORDER BY total DESC
            """,
            (user_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def set_budget(user_id: int, category: str, transaction_type: str, monthly_limit: float | None = None) -> str:
    """Creates or updates (if one already exists for this user+category) the
    category's budget row, and returns its uuid. `monthly_limit=None` means no
    limit; for an income category (which has no budget concept) no `budgets`
    row is created at all — only the category itself is ensured to exist.

    `category` is normalized to lowercase so budgets are matched case-insensitively
    against transaction categories (see add_transaction)."""
    if transaction_type not in ("income", "expense"):
        raise ValueError(f"transaction_type must be 'income' or 'expense', got {transaction_type!r}")

    category = category.strip().lower()
    with db_connection() as conn:
        category_uuid = _find_or_create_category(conn, category, transaction_type)

        if transaction_type == "income":
            conn.commit()
            return category_uuid

        existing = conn.execute(
            "SELECT uuid FROM budgets WHERE user_id = ? AND category_uuid = ?",
            (user_id, category_uuid),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE budgets SET limit_amount = ? WHERE uuid = ?",
                (monthly_limit, existing[0]),
            )
            budget_uuid = existing[0]
        else:
            budget_uuid = str(uuid_lib.uuid4())
            conn.execute(
                "INSERT INTO budgets (uuid, period_type, limit_amount, user_id, category_uuid) "
                "VALUES (?, 'monthly', ?, ?, ?)",
                (budget_uuid, monthly_limit, user_id, category_uuid),
            )

        conn.commit()
        return budget_uuid


def get_categories(user_id: int, transaction_type: str) -> dict:
    """Returns {category: monthly_limit} for every category of `transaction_type`
    that exists — this is what the category-selection menu is built from (the
    database is the only source; there is no parallel Python category list).
    `categories` is a shared catalog (not scoped to any one user), so this
    lists the full catalog for that type; only the *limit* is personal,
    sourced from `user_id`'s own `budgets` row for that category (left join,
    so it comes back as None if they don't have one — always the case for
    income, which has no budget concept)."""
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.name, b.limit_amount
            FROM categories c
            LEFT JOIN budgets b ON b.category_uuid = c.uuid AND b.user_id = ?
            WHERE c.transaction_type = ?
            ORDER BY c.name
            """,
            (user_id, transaction_type),
        ).fetchall()
    return {name: limit for name, limit in rows}


def get_budget_limits(user_id: int) -> list[dict]:
    """Returns every budgeted category for `user_id` with its all-time expense total
    and monthly limit (unlike check_budget_status, this is not scoped to the current
    month) — used to display budget status and to enforce limits when adding an
    expense.

    Categories are compared case-insensitively: a transaction's category name
    (resolved via its own `category_uuid`) is matched against the budget's
    category name with LOWER(...) on both sides, so a budget on 'Food' still
    matches a 'food' expense even if those ended up as two different
    `categories` rows."""
    with db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                LOWER(c.name) AS category,
                b.limit_amount AS monthly_limit,
                (
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM transactions t
                    JOIN categories tc ON tc.uuid = t.category_uuid
                    WHERE t.user_id = b.user_id
                        AND t.transaction_type = 'expense'
                        AND LOWER(tc.name) = LOWER(c.name)
                ) AS spent
            FROM budgets b
            JOIN categories c ON c.uuid = b.category_uuid
            WHERE b.user_id = ? AND c.transaction_type = 'expense'
            ORDER BY LOWER(c.name)
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
                LOWER(c.name) AS category,
                b.limit_amount AS monthly_limit,
                (
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM transactions t
                    JOIN categories tc ON tc.uuid = t.category_uuid
                    WHERE t.user_id = b.user_id
                        AND t.transaction_type = 'expense'
                        AND LOWER(tc.name) = LOWER(c.name)
                        AND strftime('%Y-%m', t.date) = ?
                ) AS spent
            FROM budgets b
            JOIN categories c ON c.uuid = b.category_uuid
            WHERE b.user_id = ? AND c.transaction_type = 'expense'
            ORDER BY LOWER(c.name)
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
