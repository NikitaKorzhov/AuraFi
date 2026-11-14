CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- The shared category catalog (income and expense) — NOT owned by any one
-- user (no user_id here). Every user picks from the same list; what's
-- personal to a user is only their `budgets` row (the limit) and their own
-- `transactions`, both of which point into this table by `category_uuid`.
CREATE TABLE IF NOT EXISTS categories (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    category_uuid TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (category_uuid) REFERENCES categories (uuid)
);

-- A budget constraint on one category. Income has no budget concept, so an
-- income category never gets a row here (see `categories` for those). No
-- `name` column — a budget's display name is always its linked category's
-- name (joined via `category_uuid`), never stored redundantly here.
CREATE TABLE IF NOT EXISTS budgets (
    uuid TEXT PRIMARY KEY,
    period_type TEXT NOT NULL CHECK (period_type IN ('monthly', 'yearly')) DEFAULT 'monthly',
    limit_amount REAL,
    user_id INTEGER NOT NULL,
    category_uuid TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (category_uuid) REFERENCES categories (uuid)
);
