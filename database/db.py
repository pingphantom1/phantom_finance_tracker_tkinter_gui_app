"""
database/db.py
Handles SQLite database initialization and all query operations.
All account and transaction queries are scoped to a user_id for data isolation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from auth.auth import hash_password, verify_password

DB_PATH = Path(__file__).parent.parent / "phantom_finance.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database with FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db() -> None:
    """Create all tables if they do not already exist, and run any pending migrations."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                type       TEXT    NOT NULL,
                balance    REAL    NOT NULL DEFAULT 0.0,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id  INTEGER NOT NULL,
                type        TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                description TEXT,
                date        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                key        TEXT    NOT NULL,
                value      TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (user_id, key)
            )
        """)

        conn.commit()

    _run_migrations()


def _run_migrations() -> None:
    """Apply incremental schema changes to existing databases."""
    with get_connection() as conn:
        # Migration 1: add user_id column to accounts if it doesn't exist yet
        # (handles databases created before the auth feature was added)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE accounts ADD COLUMN user_id INTEGER")
            conn.commit()


# ---------------------------------------------------------------------------
# User auth queries
# ---------------------------------------------------------------------------

def register_user(username: str, password: str) -> int | None:
    """
    Create a new user. Returns the new user's id on success,
    or None if the username is already taken.
    """
    stored_hash = hash_password(password)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username.strip(), stored_hash),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None  # username taken


def verify_user(username: str, password: str) -> int | None:
    """
    Verify a login attempt. Returns the user's id on success,
    or None if credentials are invalid.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return row["id"]
    return None


def get_username(user_id: int) -> str:
    """Return the username for the given user_id."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return row["username"] if row else ""


# ---------------------------------------------------------------------------
# Account queries (all scoped to user_id)
# ---------------------------------------------------------------------------

def get_all_accounts(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM accounts WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()


def get_account_by_id(account_id: int, user_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id),
        ).fetchone()


def insert_account(user_id: int, name: str, account_type: str, balance: float = 0.0) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
            (user_id, name, account_type, balance),
        )
        conn.commit()
        return cursor.lastrowid


def update_account(account_id: int, user_id: int, name: str, account_type: str, balance: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE accounts SET name = ?, type = ?, balance = ? WHERE id = ? AND user_id = ?",
            (name, account_type, balance, account_id, user_id),
        )
        conn.commit()


def delete_account(account_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Transaction queries (isolated via accounts.user_id)
# ---------------------------------------------------------------------------

def get_all_transactions(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, a.name AS account_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            ORDER BY t.date DESC, t.created_at DESC
        """, (user_id,)).fetchall()


def get_transactions_by_type(user_id: int, transaction_type: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, a.name AS account_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? AND t.type = ?
            ORDER BY t.date DESC
        """, (user_id, transaction_type)).fetchall()


def insert_transaction(
    account_id: int,
    transaction_type: str,
    category: str,
    amount: float,
    description: str,
    date: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO transactions (account_id, type, category, amount, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (account_id, transaction_type, category, amount, description, date))
        conn.commit()
        return cursor.lastrowid


def update_transaction(
    transaction_id: int,
    account_id: int,
    transaction_type: str,
    category: str,
    amount: float,
    description: str,
    date: str,
) -> None:
    with get_connection() as conn:
        conn.execute("""
            UPDATE transactions
            SET account_id = ?, type = ?, category = ?, amount = ?, description = ?, date = ?
            WHERE id = ?
        """, (account_id, transaction_type, category, amount, description, date, transaction_id))
        conn.commit()


def delete_transaction(transaction_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()


def get_summary(user_id: int) -> dict:
    """Return total income, total expenses, and net balance for a specific user."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN t.type = 'income'  THEN t.amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS total_expenses
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
        """, (user_id,)).fetchone()
        return {
            "total_income": row["total_income"],
            "total_expenses": row["total_expenses"],
            "net_balance": row["total_income"] - row["total_expenses"],
        }


# ---------------------------------------------------------------------------
# User settings queries
# ---------------------------------------------------------------------------

# Defaults applied the first time a key is read for a new user.
SETTING_DEFAULTS: dict[str, str] = {
    "currency_symbol":  "$",
    "currency_name":    "US Dollar",
    "theme":            "darkly",
    "date_format":      "%b %d, %Y",
    "default_account":  "",          # account name; empty means no preference
}


def get_setting(user_id: int, key: str) -> str:
    """Return the value of a setting, falling back to the default if not yet saved."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
            (user_id, key),
        ).fetchone()
    if row:
        return row["value"]
    return SETTING_DEFAULTS.get(key, "")


def set_setting(user_id: int, key: str, value: str) -> None:
    """Insert or update a single setting for the user."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_settings (user_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, key) DO UPDATE SET value = excluded.value
        """, (user_id, key, value))
        conn.commit()


def get_all_settings(user_id: int) -> dict[str, str]:
    """Return all settings for the user, merged with defaults for any missing keys."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    saved = {row["key"]: row["value"] for row in rows}
    # Start from defaults so every key is always present
    result = dict(SETTING_DEFAULTS)
    result.update(saved)
    return result


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    """
    Change the user's password after verifying the current one.
    Returns True on success, False if the current password is wrong.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if not row or not verify_password(current_password, row["password_hash"]):
        return False
    new_hash = hash_password(new_password)
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )
        conn.commit()
    return True
