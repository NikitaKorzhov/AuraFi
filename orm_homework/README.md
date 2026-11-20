# orm_homework/ — Homework 36 (SQLAlchemy ORM)

Standalone exercises for Homework 36. The real migration — the thing that
actually matters — lives in the live app: root `database.py` (SQLAlchemy
engine/session setup) and root `models.py` (the `User`/`Category`/
`Transaction`/`Budget` ORM models, plus every CRUD function rewritten to
query through a `Session` instead of raw SQL). Everything in this folder
**reuses those same modules directly** instead of duplicating them.

See the repo root `README.md`'s "Phase 5 Branch Progress" entry and
`CLAUDE.md` for the full story of what changed and why.

## Files

| File | Task | What it does |
|---|---|---|
| `init_db.py` | 4 | Runnable entry point: `init_db()` + lists the created tables |
| `crud_operations.py` | 5 | `UserCRUD`/`TransactionCRUD` — class-based CRUD, same ORM models as the live app |
| `test_crud.py` | 6 | Demo script exercising both CRUD classes against real data (prints, not assertions) |
| `advanced_queries.py` | 7 | Search (`ILIKE`), grouped counts, pagination — genuinely new, nothing in the live app needed this before |
| `migration_example.py` | 8 | Raw SQL vs ORM, the same 4 operations side by side, with a real line-count comparison (not a claimed one) |
| `complex_relationships.py` | 9* (bonus) | `joinedload`/`selectinload` eager loading + aggregate statistics |
| `test_models_sqlite.py` | 10* (bonus) | **Real pytest suite**, run against an **in-memory SQLite** engine instead of PostgreSQL — proof the ORM models/functions in root `models.py` are actually engine-portable, not Postgres-specific code in an ORM costume |

`migration_example.py` is a side-by-side comparison for the checklist item,
not the real migration itself — that already happened in place, in the live
`models.py` (see its module docstring and the README/CLAUDE.md entries for
the full before/after).

## Running

```bash
# from the repo root, with the venv from requirements.txt active
python -m orm_homework.init_db
python -m orm_homework.crud_operations
python -m orm_homework.test_crud
python -m orm_homework.advanced_queries
python -m orm_homework.migration_example
python -m orm_homework.complex_relationships

# the bonus pytest suite (SQLite, no PostgreSQL server needed for this one)
pytest orm_homework/test_models_sqlite.py -v
```

`init_db.py`/`crud_operations.py`/`test_crud.py`/`advanced_queries.py` all
run against the **real** `PG_DB` database (same as the live app) — their
demo rows are created and deleted again within each run, so nothing is left
behind for the real app's own data to trip over.
