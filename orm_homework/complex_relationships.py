"""Homework 36, Task 9 (bonus): advanced relationships and eager loading.

Genuinely new capability: nothing in the live app needed joinedload/
selectinload before — AuraFi only ever reads one user's own data, never a
user's full object graph (transactions + budgets together) at once.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import Budget, Transaction, User


def get_user_with_all_data(session: Session, user_id: int) -> Optional[User]:
    """Load a user with both their transactions and budgets eager-loaded in
    one round trip (joinedload) — instead of a separate lazy-load per
    `user.transactions`/`user.budgets` access."""
    result = session.execute(
        select(User)
        .options(joinedload(User.transactions), joinedload(User.budgets))
        .where(User.id == user_id)
    )
    return result.unique().scalar_one_or_none()


def get_all_users_with_budgets(session: Session) -> list[User]:
    """selectinload — a second, separate query loads every user's budgets in
    one go; usually the better choice than joinedload for a one-to-many."""
    result = session.execute(select(User).options(selectinload(User.budgets)))
    return result.scalars().unique().all()


def get_transaction_statistics(session: Session) -> dict:
    """Aggregate statistics across every transaction in the database."""
    total_transactions, distinct_users, distinct_types = session.execute(
        select(
            func.count(Transaction.id),
            func.count(func.distinct(Transaction.user_id)),
            func.count(func.distinct(Transaction.transaction_type)),
        )
    ).one()

    return {
        "total_transactions": total_transactions,
        "distinct_users": distinct_users,
        "distinct_transaction_types": distinct_types,
    }


def get_budget_statistics(session: Session) -> dict:
    """Aggregate statistics across every budget in the database."""
    total_budgets, total_limit = session.execute(
        select(func.count(Budget.uuid), func.coalesce(func.sum(Budget.limit_amount), 0))
    ).one()

    return {"total_budgets": total_budgets, "total_limit_amount": total_limit}


if __name__ == "__main__":
    from database import SessionLocal, init_db

    init_db()
    session = SessionLocal()

    print("=== COMPLEX RELATIONSHIPS ===\n")
    print("Transaction statistics:", get_transaction_statistics(session))
    print("Budget statistics:", get_budget_statistics(session))

    users_with_budgets = get_all_users_with_budgets(session)
    print(f"\nUsers with eager-loaded budgets ({len(users_with_budgets)}):")
    for user in users_with_budgets:
        print(f"  - {user.username}: {len(user.budgets)} budget(s)")

    session.close()
