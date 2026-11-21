"""Homework 36 (SQLAlchemy ORM) standalone exercises.

The real migration lives in the live app (root database.py/models.py — see
their docstrings and CLAUDE.md). Everything here reuses those same modules
directly rather than duplicating them: a class-based CRUD demo, eager-loading
query examples, and a proof that the ORM models are genuinely engine-portable
(the same models/functions run unchanged against SQLite, not just Postgres).
"""
