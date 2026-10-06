"""
utils/helpers.py
Shared utility functions used across the application.
"""

from datetime import datetime, date


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format a float as a currency string, e.g. 1234.5 -> '$1,234.50'"""
    return f"{symbol}{amount:,.2f}"


def today_str() -> str:
    """Return today's date as an ISO 8601 string (YYYY-MM-DD)."""
    return date.today().isoformat()


def format_date(date_str: str, fmt: str = "%b %d, %Y") -> str:
    """Convert an ISO 8601 date string to a human-readable format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime(fmt)
    except ValueError:
        return date_str


def parse_date(date_str: str) -> date | None:
    """Parse an ISO 8601 date string into a date object. Returns None on failure."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min_val and max_val."""
    return max(min_val, min(value, max_val))
