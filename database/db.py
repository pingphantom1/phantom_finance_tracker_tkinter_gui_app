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

        # transfers links the two transaction rows (debit + credit) that form one
        # logical transfer so they can be deleted together atomically.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                debit_tx_id     INTEGER NOT NULL UNIQUE,
                credit_tx_id    INTEGER NOT NULL UNIQUE,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (debit_tx_id)  REFERENCES transactions(id) ON DELETE CASCADE,
                FOREIGN KEY (credit_tx_id) REFERENCES transactions(id) ON DELETE CASCADE
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

        # Migration 2: create transfers table for databases created before this feature
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "transfers" not in tables:
            conn.execute("""
                CREATE TABLE transfers (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    debit_tx_id     INTEGER NOT NULL UNIQUE,
                    credit_tx_id    INTEGER NOT NULL UNIQUE,
                    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (debit_tx_id)  REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (credit_tx_id) REFERENCES transactions(id) ON DELETE CASCADE
                )
            """)
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
    user_id: int,
    account_id: int,
    transaction_type: str,
    category: str,
    amount: float,
    description: str,
    date: str,
) -> None:
    """Update a transaction only if it belongs to user_id (ownership enforced via JOIN)."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE transactions
            SET account_id = ?, type = ?, category = ?, amount = ?, description = ?, date = ?
            WHERE id = ?
              AND EXISTS (
                  SELECT 1 FROM accounts
                  WHERE accounts.id = transactions.account_id
                    AND accounts.user_id = ?
              )
        """, (account_id, transaction_type, category, amount, description, date,
              transaction_id, user_id))
        conn.commit()


def delete_transaction(transaction_id: int, user_id: int) -> None:
    """Delete a transaction only if it belongs to user_id (ownership enforced via JOIN)."""
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM transactions
            WHERE id = ?
              AND EXISTS (
                  SELECT 1 FROM accounts
                  WHERE accounts.id = transactions.account_id
                    AND accounts.user_id = ?
              )
        """, (transaction_id, user_id))
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


# ---------------------------------------------------------------------------
# Transfer queries
# ---------------------------------------------------------------------------

def record_transfer(
    user_id: int,
    from_account_id: int,
    to_account_id: int,
    amount: float,
    description: str,
    date: str,
) -> tuple[int, int]:
    """
    Move `amount` from one account to another atomically.

    Creates two transaction rows (debit on source, credit on destination),
    links them in the transfers table, and adjusts both account balances —
    all inside a single DB transaction so it is all-or-nothing.

    Returns (debit_tx_id, credit_tx_id).
    Raises ValueError if either account does not belong to user_id, or if
    from_account_id == to_account_id.
    """
    if from_account_id == to_account_id:
        raise ValueError("Source and destination accounts must be different.")

    with get_connection() as conn:
        # Ownership check — both accounts must belong to this user
        src = conn.execute(
            "SELECT id, balance FROM accounts WHERE id = ? AND user_id = ?",
            (from_account_id, user_id),
        ).fetchone()
        dst = conn.execute(
            "SELECT id, balance FROM accounts WHERE id = ? AND user_id = ?",
            (to_account_id, user_id),
        ).fetchone()
        if src is None or dst is None:
            raise ValueError("One or both accounts not found for this user.")

        note = description.strip() or "Transfer"

        # Debit the source account
        debit_cur = conn.execute("""
            INSERT INTO transactions (account_id, type, category, amount, description, date)
            VALUES (?, 'expense', 'Transfer', ?, ?, ?)
        """, (from_account_id, amount, note, date))
        debit_id = debit_cur.lastrowid

        # Credit the destination account
        credit_cur = conn.execute("""
            INSERT INTO transactions (account_id, type, category, amount, description, date)
            VALUES (?, 'income', 'Transfer', ?, ?, ?)
        """, (to_account_id, amount, note, date))
        credit_id = credit_cur.lastrowid

        # Link the pair
        conn.execute("""
            INSERT INTO transfers (debit_tx_id, credit_tx_id) VALUES (?, ?)
        """, (debit_id, credit_id))

        # Adjust balances
        conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            (amount, from_account_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, to_account_id),
        )

        conn.commit()
    return debit_id, credit_id


def delete_transfer(transfer_debit_tx_id: int, user_id: int) -> bool:
    """
    Delete a transfer by the debit transaction's id, reversing both account
    balances atomically. Ownership is verified — only the owning user can delete.

    Returns True on success, False if the transfer was not found or not owned
    by user_id.
    """
    with get_connection() as conn:
        row = conn.execute("""
            SELECT tf.debit_tx_id, tf.credit_tx_id,
                   td.amount, td.account_id AS debit_account_id,
                   tc.account_id AS credit_account_id
            FROM transfers tf
            JOIN transactions td ON tf.debit_tx_id  = td.id
            JOIN transactions tc ON tf.credit_tx_id = tc.id
            JOIN accounts     ad ON td.account_id   = ad.id
            WHERE tf.debit_tx_id = ? AND ad.user_id = ?
        """, (transfer_debit_tx_id, user_id)).fetchone()

        if row is None:
            return False

        amount           = row["amount"]
        debit_account_id = row["debit_account_id"]
        credit_account_id= row["credit_account_id"]
        debit_id         = row["debit_tx_id"]
        credit_id        = row["credit_tx_id"]

        # Reverse the balance changes
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, debit_account_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            (amount, credit_account_id),
        )

        # Cascade will remove the transfers row when the transactions are deleted
        conn.execute("DELETE FROM transactions WHERE id = ?", (debit_id,))
        conn.execute("DELETE FROM transactions WHERE id = ?", (credit_id,))

        conn.commit()
    return True


def get_filtered_transactions(
    user_id: int,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    tx_type: str | None = None,
    account_id: int | None = None,
    keyword: str | None = None,
) -> list[sqlite3.Row]:
    """
    Return transactions matching all supplied filters, newest first.

    Parameters
    ----------
    user_id    : Scopes results to this user.
    date_from  : ISO 8601 string (YYYY-MM-DD), inclusive lower bound.
    date_to    : ISO 8601 string (YYYY-MM-DD), inclusive upper bound.
    tx_type    : 'income', 'expense', or 'transfer' (matches category='Transfer').
                 None means all types.
    account_id : Restrict to a specific account (must belong to user_id).
    keyword    : Case-insensitive substring search over description and category.
    """
    clauses: list[str] = ["a.user_id = ?"]
    params:  list      = [user_id]

    if date_from:
        clauses.append("t.date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("t.date <= ?")
        params.append(date_to)
    if tx_type == "transfer":
        clauses.append("t.category = 'Transfer'")
    elif tx_type in ("income", "expense"):
        clauses.append("t.type = ?")
        clauses.append("t.category != 'Transfer'")
        params.append(tx_type)
    if account_id is not None:
        clauses.append("t.account_id = ?")
        params.append(account_id)
    if keyword:
        clauses.append("(LOWER(t.description) LIKE ? OR LOWER(t.category) LIKE ?)")
        like = f"%{keyword.lower()}%"
        params.extend([like, like])

    where = " AND ".join(clauses)
    sql = f"""
        SELECT t.*, a.name AS account_name,
               CASE WHEN tf.id IS NOT NULL THEN 1 ELSE 0 END AS is_transfer,
               tf.debit_tx_id, tf.credit_tx_id
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        LEFT JOIN transfers tf
               ON (tf.debit_tx_id = t.id OR tf.credit_tx_id = t.id)
        WHERE {where}
        ORDER BY t.date DESC, t.created_at DESC
    """
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()
