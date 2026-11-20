-- PostgreSQL translation of AuraFi's init.sql (SQLite). Same four tables,
-- same relationships; integer PKs become SERIAL, money columns become
-- NUMERIC instead of REAL, and the user_id foreign keys cascade on delete
-- so removing a user cleans up their own transactions/budgets.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- Shared category catalog (income and expense) — not owned by any one user.
CREATE TABLE IF NOT EXISTS categories (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    category_uuid TEXT NOT NULL REFERENCES categories (uuid),
    date DATE NOT NULL,
    description TEXT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE
);

-- A budget constraint on one category. Income has no budget concept, so an
-- income category never gets a row here. No `name` column — a budget's
-- display name is always its linked category's name, joined via category_uuid.
CREATE TABLE IF NOT EXISTS budgets (
    uuid TEXT PRIMARY KEY,
    period_type TEXT NOT NULL CHECK (period_type IN ('monthly', 'yearly')) DEFAULT 'monthly',
    limit_amount NUMERIC(12, 2),
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    category_uuid TEXT NOT NULL REFERENCES categories (uuid)
);
