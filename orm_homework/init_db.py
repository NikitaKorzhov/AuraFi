"""Homework 36, Task 4: initialize the database and list its tables.

Thin wrapper over the live database.py/models.py — they already do the real
work; this is just the runnable entry point the homework spec asks for.
"""

from database import Base, init_db
from models import Budget, Category, Transaction, User  # noqa: F401 — registers tables on Base.metadata

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Tables created successfully!")

    print("\nTables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
