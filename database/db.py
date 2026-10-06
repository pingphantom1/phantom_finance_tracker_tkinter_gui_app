"""
database/db.py
Handles SQLite database initialization and all query operations.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "phantom_finance.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows accessible by column name
    return conn


def initialize_db() -> None:
    """Create all tables if they do not already exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT    NOT NULL UNIQUE,
                type    TEXT    NOT NULL,  -- e.g. 'bank', 'cash', 'credit'
                balance REAL    NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id  INTEGER NOT NULL,
                type        TEXT    NOT NULL,  -- 'income' or 'expense'
                category    TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                description TEXT,
                date        TEXT    NOT NULL,  -- ISO 8601: YYYY-MM-DD
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)

        conn.commit()


# ---------------------------------------------------------------------------
# Account queries
# ---------------------------------------------------------------------------

def get_all_accounts() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()


def get_account_by_id(account_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()


def insert_account(name: str, account_type: str, balance: float = 0.0) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
            (name, account_type, balance),
        )
        conn.commit()
        return cursor.lastrowid


def update_account(account_id: int, name: str, account_type: str, balance: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE accounts SET name = ?, type = ?, balance = ? WHERE id = ?",
            (name, account_type, balance, account_id),
        )
        conn.commit()


def delete_account(account_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Transaction queries
# ---------------------------------------------------------------------------

def get_all_transactions() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, a.name AS account_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            ORDER BY t.date DESC, t.created_at DESC
        """).fetchall()


def get_transactions_by_type(transaction_type: str) -> list[sqlite3.Row]:
    """transaction_type: 'income' or 'expense'"""
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, a.name AS account_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.type = ?
            ORDER BY t.date DESC
        """, (transaction_type,)).fetchall()


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


def get_summary() -> dict:
    """Return total income, total expenses, and net balance."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expenses
            FROM transactions
        """).fetchone()
        return {
            "total_income": row["total_income"],
            "total_expenses": row["total_expenses"],
            "net_balance": row["total_income"] - row["total_expenses"],
        }
