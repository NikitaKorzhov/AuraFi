"""Homework 36, Task 5: CRUD operations via SQLAlchemy ORM classes.

A class-based demonstration (UserCRUD.create/get_by_id/...) of the same
capability that already lives, function-style, in the root models.py (which
main.py/expense_tracker/ actually call) — built on the exact same ORM models,
not a parallel/duplicate schema.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models import Transaction, User


class UserCRUD:
    @staticmethod
    def create(session: Session, username: str, email: str, password_hash: str) -> User:
        """Create a user."""
        user = User(username=username, email=email, password_hash=password_hash)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def get_by_id(session: Session, user_id: int) -> Optional[User]:
        """Get by id."""
        return session.get(User, user_id)

    @staticmethod
    def get_by_username(session: Session, username: str) -> Optional[User]:
        """Get by username."""
        return session.query(User).filter(User.username == username).first()

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 10) -> list[User]:
        """Get all, paginated."""
        return session.query(User).order_by(User.id).offset(skip).limit(limit).all()

    @staticmethod
    def update(session: Session, user_id: int, **kwargs) -> Optional[User]:
        """Update a user."""
        user = session.get(User, user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            session.refresh(user)
        return user

    @staticmethod
    def delete(session: Session, user_id: int) -> bool:
        """Delete a user."""
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False


class TransactionCRUD:
    @staticmethod
    def create(
        session: Session,
        user_id: int,
        amount: float,
        transaction_type: str,
        category_uuid: str,
        date: str,
    ) -> Transaction:
        """Create a transaction."""
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            category_uuid=category_uuid,
            date=date,
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    @staticmethod
    def get_by_id(session: Session, transaction_id: int) -> Optional[Transaction]:
        """Get by id."""
        return session.get(Transaction, transaction_id)

    @staticmethod
    def get_by_user(session: Session, user_id: int) -> list[Transaction]:
        """Get every transaction belonging to a user."""
        return session.query(Transaction).filter(Transaction.user_id == user_id).all()

    @staticmethod
    def delete(session: Session, transaction_id: int) -> bool:
        """Delete a transaction."""
        transaction = session.get(Transaction, transaction_id)
        if transaction:
            session.delete(transaction)
            session.commit()
            return True
        return False


if __name__ == "__main__":
    import uuid

    from database import SessionLocal, init_db
    from models import Category

    init_db()
    session = SessionLocal()

    print("CREATE — user")
    user = UserCRUD.create(session, "crud_demo_user", "crud_demo@example.com", "hash")
    print(f"created: {user}\n")

    print("READ — by username")
    print(f"found: {UserCRUD.get_by_username(session, 'crud_demo_user')}\n")

    print("UPDATE — email")
    updated = UserCRUD.update(session, user.id, email="crud_demo_new@example.com")
    print(f"updated: {updated}\n")

    print("CREATE — a category + transaction for this user")
    category = Category(uuid=str(uuid.uuid4()), name="crud-demo", transaction_type="expense")
    session.add(category)
    session.commit()
    transaction = TransactionCRUD.create(session, user.id, 10.0, "expense", category.uuid, "2026-11-20")
    print(f"created: {transaction}\n")

    print("DELETE — transaction, category, user (FK order)")
    print(f"transaction deleted: {TransactionCRUD.delete(session, transaction.id)}")
    session.delete(category)
    session.commit()
    print(f"user deleted: {UserCRUD.delete(session, user.id)}")

    session.close()
