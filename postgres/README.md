# postgres/ — Homework 30

A standalone PostgreSQL walkthrough against AuraFi's real schema
(`users`/`categories`/`transactions`/`budgets`, mirrored from the root
`init.sql`). It does not touch the live SQLite path (`database.py` / root
`models.py`) and nothing in the running app imports it — it's the first
concrete step of the README roadmap item "PostgreSQL support alongside
SQLite", kept isolated so the existing app and its test suite are
unaffected.

## Setup

Requires a running local PostgreSQL server (tested against Postgres.app on
`127.0.0.1:5432`, trust auth, no password). Connection settings are read
from `.env` (`PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, plus its own
`PG_HOMEWORK_DB` — deliberately a *different* variable from the live app's
`PG_DB`, so this homework's demo INSERT/UPDATE/DELETE/ROLLBACK scripts never
touch the same database the running app's `aurafi` data lives in — see
`.env.example`); every one of them has a default that matches a typical
local install, so none are required to just try it.

```bash
pip install -r requirements.txt
python -m postgres.schema   # creates the `aurafi_homework30` database and its tables
```

## Scripts, in the order they build on each other

| File | What it does |
|---|---|
| `db_connection.py` | First connection check — prints server version, user, db |
| `schema.sql` / `schema.py` | Creates the `aurafi_homework30` database and its 4 tables (PK/FK) |
| `crud_operations.py` | `UserRepository` / `TransactionRepository` — Create/Read/Update/Delete |
| `parameterized_queries.py` | Safe parameterized queries vs. string-concatenated SQL |
| `join_queries.py` | INNER JOIN, LEFT JOIN, aggregation across users/transactions/categories |
| `transactions_demo.py` | A successful COMMIT and a UniqueViolation-triggered ROLLBACK |
| `information_schema_report.py` | Bonus — lists every table and column via `information_schema` |
| `connection.py` | Bonus — the two context managers (`get_db_connection`/`get_db_cursor`) everything above is built on |

Run any of them directly, e.g. `python -m postgres.crud_operations`.
Captured output from a real run of each is under `outputs/`.
