"""
utils/helpers.py
Shared utility functions used across the application.

format_currency and format_date each accept an optional `settings` dict
(as returned by db.get_all_settings) so they reflect the user's preferences.
When no settings dict is provided they fall back to sensible defaults.
"""

from __future__ import annotations

from datetime import datetime, date


def format_currency(amount: float, settings: dict | None = None) -> str:
    """
    Format a float as a currency string using the user's currency symbol.
    e.g. 1234.5 -> '$1,234.50'

    The settings dict should contain at least the key 'currency_symbol'.
    Falls back to '$' if not provided.
    """
    symbol = "$"
    if settings:
        symbol = settings.get("currency_symbol", "$")
    return f"{symbol}{amount:,.2f}"


def format_date(date_str: str, settings: dict | None = None) -> str:
    """
    Convert an ISO 8601 date string (YYYY-MM-DD) to a human-readable format
    using the user's preferred date format string.

    The settings dict should contain the key 'date_format' (a strftime pattern).
    Falls back to '%b %d, %Y' if not provided.
    """
    fmt = "%b %d, %Y"
    if settings:
        fmt = settings.get("date_format", fmt)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime(fmt)
    except ValueError:
        return date_str


def today_str() -> str:
    """Return today's date as an ISO 8601 string (YYYY-MM-DD)."""
    return date.today().isoformat()


def parse_date(date_str: str) -> date | None:
    """Parse an ISO 8601 date string into a date object. Returns None on failure."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min_val and max_val."""
    return max(min_val, min(value, max_val))
