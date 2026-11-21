"""Homework 36, Task 7: complex queries — filtering, JOIN, aggregation.

Genuinely new capability, not a rewrite of something that already existed:
the live app never needed grouped counts or a search-by-description before.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Transaction, User


def search_transactions_by_description(session: Session, search_term: str) -> list[Transaction]:
    """Case-insensitive substring search (ILIKE)."""
    return session.scalars(
        select(Transaction).where(Transaction.description.ilike(f"%{search_term}%"))
    ).all()


def get_transaction_count_by_type(session: Session) -> list[tuple]:
    """Count transactions grouped by type (income/expense)."""
    return session.execute(
        select(Transaction.transaction_type, func.count(Transaction.id)).group_by(
            Transaction.transaction_type
        )
    ).all()


def get_user_transaction_counts(session: Session) -> list[tuple]:
    """Count transactions per user (JOIN + GROUP BY)."""
    return session.execute(
        select(User.username, func.count(Transaction.id))
        .join(Transaction, Transaction.user_id == User.id)
        .group_by(User.id, User.username)
    ).all()


def get_paged_transactions(session: Session, user_id: int, page: int = 1, per_page: int = 10) -> dict:
    """Paginated transaction listing for one user."""
    offset = (page - 1) * per_page

    total = session.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user_id))
    transactions = session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.date, Transaction.id)
        .offset(offset)
        .limit(per_page)
    ).all()
    total_pages = (total + per_page - 1) // per_page

    return {"transactions": transactions, "total": total, "page": page, "total_pages": total_pages}


if __name__ == "__main__":
    from database import SessionLocal, init_db

    init_db()
    session = SessionLocal()

    print("=== ADVANCED QUERIES ===\n")
    print("Transaction counts by type:", get_transaction_count_by_type(session))
    print("Transaction counts by user:", get_user_transaction_counts(session))
    print("Transactions matching 'food':", search_transactions_by_description(session, "food"))

    session.close()
