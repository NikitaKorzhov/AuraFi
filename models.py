from __future__ import annotations

import hashlib
import hmac
import os
import uuid as uuid_lib
from datetime import date as date_cls
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Text, case, delete, func, select
from sqlalchemy.orm import Mapped, aliased, mapped_column, relationship

from database import Base, SessionLocal

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
# limit as None (see get_categories()'s outer join).
DEFAULT_INCOME_CATEGORIES = ["salary", "freelance", "gift", "other"]


# ---------------------------------------------------------------------------
# ORM models (Homework 36, Task 3) — declared on database.Base, created via
# database.init_db()'s Base.metadata.create_all(). Column types stay engine-
# generic (Text/Float, not postgresql.TEXT/REAL) so the same models also work
# unchanged against SQLite — see orm_homework/test_models_sqlite.py.
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"


class Category(Base):
    """Shared catalog (income and expense) — not owned by any one user (no
    user_id here). Every user picks from the same list; what's personal to a
    user is only their `budgets` row (the limit) and their own
    `transactions`, both of which point into this table by `category_uuid`."""

    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("transaction_type IN ('income', 'expense')"),)

    uuid: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_type: Mapped[str] = mapped_column(Text, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(uuid={self.uuid!r}, name={self.name!r})>"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("transaction_type IN ('income', 'expense')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[float] = mapped_column(nullable=False)
    transaction_type: Mapped[str] = mapped_column(Text, nullable=False)
    category_uuid: Mapped[str] = mapped_column(ForeignKey("categories.uuid"), nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="transactions")
    category: Mapped["Category"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, amount={self.amount}, type={self.transaction_type})>"


class Budget(Base):
    """A budget constraint on one category. Income has no budget concept, so
    an income category never gets a row here. No `name` column — a budget's
    display name is always its linked category's name, joined via category_uuid."""

    __tablename__ = "budgets"
    __table_args__ = (CheckConstraint("period_type IN ('monthly', 'yearly')"),)

    uuid: Mapped[str] = mapped_column(Text, primary_key=True)
    period_type: Mapped[str] = mapped_column(Text, nullable=False, default="monthly")
    limit_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_uuid: Mapped[str] = mapped_column(ForeignKey("categories.uuid"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="budgets")
    category: Mapped["Category"] = relationship(back_populates="budgets")

    def __repr__(self) -> str:
        return f"<Budget(uuid={self.uuid!r}, limit_amount={self.limit_amount})>"


# ---------------------------------------------------------------------------
# Public API (Homework 36, Tasks 5 & 8 — CRUD via the ORM, replacing the raw
# psycopg/SQL this used to run). Same function signatures and return shapes
# as before the migration, so expense_tracker/ and main.py needed zero changes.
# ---------------------------------------------------------------------------


def _find_or_create_category(session, name: str, transaction_type: str) -> str:
    """Finds the existing category row (matched case-insensitively) or creates
    one, and returns its uuid. `categories` is a shared catalog — not scoped to
    any one user — so this lookup is global. Does not commit — caller owns the
    transaction."""
    category = session.scalar(
        select(Category).where(
            Category.transaction_type == transaction_type,
            func.lower(Category.name) == name,
        )
    )
    if category:
        return category.uuid

    category_uuid = str(uuid_lib.uuid4())
    session.add(Category(uuid=category_uuid, name=name, transaction_type=transaction_type))
    session.flush()  # visible to subsequent queries in this session before commit
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
    with SessionLocal() as session:
        user = User(username=username, email=email, password_hash=_hash_password(password))
        session.add(user)
        session.flush()  # raises here on a duplicate email, before any seeding
        user_id = user.id

        if seed_default_categories:
            for category, limit in DEFAULT_EXPENSE_CATEGORIES.items():
                category_uuid = _find_or_create_category(session, category, "expense")
                session.add(
                    Budget(
                        uuid=str(uuid_lib.uuid4()),
                        period_type="monthly",
                        limit_amount=limit,
                        user_id=user_id,
                        category_uuid=category_uuid,
                    )
                )
            for category in DEFAULT_INCOME_CATEGORIES:
                _find_or_create_category(session, category, "income")

        session.commit()
        return user_id


def authenticate_user(email: str, password: str) -> int | None:
    """Looks up the user by email and verifies the password against its stored
    hash. Returns the user id on success, None on no-match (unknown email or
    wrong password — both reported identically to the caller)."""
    with SessionLocal() as session:
        row = session.execute(
            select(User.id, User.password_hash).where(User.email == email)
        ).first()

    if row is None:
        return None

    user_id, password_hash = row
    return user_id if _verify_password(password, password_hash) else None


def get_username_by_email(email: str) -> str | None:
    """Looks up the username for `email` without checking a password — used to
    attribute a login attempt (successful or failed) to a username in logs."""
    with SessionLocal() as session:
        return session.scalar(select(User.username).where(User.email == email))


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

    with SessionLocal() as session:
        category_uuid = _find_or_create_category(session, category, transaction_type)
        transaction = Transaction(
            amount=amount,
            transaction_type=transaction_type,
            category_uuid=category_uuid,
            date=date,
            description=description,
            user_id=user_id,
        )
        session.add(transaction)
        session.flush()
        transaction_id = transaction.id
        session.commit()
        return transaction_id


def get_all_transactions(user_id: int) -> list[dict]:
    """Returns every transaction belonging to `user_id`, oldest first. `category`
    in each row is the category's name, resolved via `category_uuid` — callers
    never see the uuid, only the name (same shape as before this was a FK)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Transaction.id,
                Transaction.amount,
                Transaction.transaction_type,
                Category.name.label("category"),
                Transaction.date,
                Transaction.description,
                Transaction.user_id,
            )
            .join(Category, Category.uuid == Transaction.category_uuid)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date, Transaction.id)
        ).all()
    return [row._asdict() for row in rows]


def get_balance(user_id: int) -> float:
    """Returns income minus expenses for `user_id`."""
    with SessionLocal() as session:
        total = session.scalar(
            select(
                func.sum(
                    case(
                        (Transaction.transaction_type == "income", Transaction.amount),
                        else_=-Transaction.amount,
                    )
                )
            ).where(Transaction.user_id == user_id)
        )
    return total or 0.0


def get_expenses_by_category(user_id: int) -> list[dict]:
    """Returns total expenses per category for `user_id`, highest spend first.

    Grouped by LOWER(category name) so 'Food' and 'food' are treated as the
    same category, even if they ended up as two different `categories` rows
    (defensive against any mixed-case category data, e.g. written directly
    rather than through add_transaction's normalization)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                func.lower(Category.name).label("category"),
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Category.uuid == Transaction.category_uuid)
            .where(Transaction.user_id == user_id, Transaction.transaction_type == "expense")
            .group_by(func.lower(Category.name))
            .order_by(func.sum(Transaction.amount).desc())
        ).all()
    return [row._asdict() for row in rows]


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
    with SessionLocal() as session:
        category_uuid = _find_or_create_category(session, category, transaction_type)

        if transaction_type == "income":
            session.commit()
            return category_uuid

        existing = session.scalar(
            select(Budget).where(Budget.user_id == user_id, Budget.category_uuid == category_uuid)
        )
        if existing:
            existing.limit_amount = monthly_limit
            budget_uuid = existing.uuid
        else:
            budget_uuid = str(uuid_lib.uuid4())
            session.add(
                Budget(
                    uuid=budget_uuid,
                    period_type="monthly",
                    limit_amount=monthly_limit,
                    user_id=user_id,
                    category_uuid=category_uuid,
                )
            )

        session.commit()
        return budget_uuid


def get_categories(user_id: int, transaction_type: str) -> dict:
    """Returns {category: monthly_limit} for every category of `transaction_type`
    that exists — this is what the category-selection menu is built from (the
    database is the only source; there is no parallel Python category list).
    `categories` is a shared catalog (not scoped to any one user), so this
    lists the full catalog for that type; only the *limit* is personal,
    sourced from `user_id`'s own `budgets` row for that category (outer join,
    so it comes back as None if they don't have one — always the case for
    income, which has no budget concept)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(Category.name, Budget.limit_amount)
            .outerjoin(Budget, (Budget.category_uuid == Category.uuid) & (Budget.user_id == user_id))
            .where(Category.transaction_type == transaction_type)
            .order_by(Category.name)
        ).all()
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
    tx_category = aliased(Category)
    with SessionLocal() as session:
        spent = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .select_from(Transaction)
            .join(tx_category, tx_category.uuid == Transaction.category_uuid)
            .where(
                Transaction.user_id == Budget.user_id,
                Transaction.transaction_type == "expense",
                func.lower(tx_category.name) == func.lower(Category.name),
            )
            .scalar_subquery()
        )
        rows = session.execute(
            select(
                func.lower(Category.name).label("category"),
                Budget.limit_amount.label("monthly_limit"),
                spent.label("spent"),
            )
            .join(Category, Category.uuid == Budget.category_uuid)
            .where(Budget.user_id == user_id, Category.transaction_type == "expense")
            .order_by(func.lower(Category.name))
        ).all()
    return [row._asdict() for row in rows]


def delete_transaction(transaction_id: int) -> bool:
    """Deletes a transaction by id. Returns True if a row was actually removed."""
    with SessionLocal() as session:
        result = session.execute(delete(Transaction).where(Transaction.id == transaction_id))
        session.commit()
        return result.rowcount > 0


def check_budget_status(user_id: int) -> list[dict]:
    """Compares this month's actual expenses per category against the configured
    monthly budget for `user_id` (JOIN transactions + budgets), prints a warning
    for every category that is over its limit, and returns the full comparison.

    Categories are compared case-insensitively, same as get_budget_limits.
    `date` is stored as a plain ISO 'YYYY-MM-DD' string (see models.Transaction),
    so the current month is matched with a LIKE prefix rather than a
    database-specific date function — this also keeps the query portable to
    SQLite (see orm_homework/test_models_sqlite.py), unlike the original's
    Postgres-only SUBSTRING()."""
    month_prefix = date_cls.today().strftime("%Y-%m")
    tx_category = aliased(Category)
    with SessionLocal() as session:
        spent = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .select_from(Transaction)
            .join(tx_category, tx_category.uuid == Transaction.category_uuid)
            .where(
                Transaction.user_id == Budget.user_id,
                Transaction.transaction_type == "expense",
                func.lower(tx_category.name) == func.lower(Category.name),
                Transaction.date.like(f"{month_prefix}%"),
            )
            .scalar_subquery()
        )
        rows = session.execute(
            select(
                func.lower(Category.name).label("category"),
                Budget.limit_amount.label("monthly_limit"),
                spent.label("spent"),
            )
            .join(Category, Category.uuid == Budget.category_uuid)
            .where(Budget.user_id == user_id, Category.transaction_type == "expense")
            .order_by(func.lower(Category.name))
        ).all()

    statuses = []
    for row in rows:
        exceeded = row.spent > row.monthly_limit
        statuses.append(
            {
                "category": row.category,
                "spent": row.spent,
                "monthly_limit": row.monthly_limit,
                "exceeded": exceeded,
            }
        )
        if exceeded:
            print(
                f"⚠️  Budget exceeded for '{row.category}': "
                f"{row.spent:.2f} spent vs {row.monthly_limit:.2f} limit"
            )

    return statuses
