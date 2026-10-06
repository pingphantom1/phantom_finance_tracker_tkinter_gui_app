"""
models/transaction.py
Data class representing a financial transaction.
"""

from dataclasses import dataclass, field
from datetime import date as Date


@dataclass
class Transaction:
    account_id: int
    type: str          # 'income' or 'expense'
    category: str
    amount: float
    date: str          # ISO 8601: YYYY-MM-DD
    description: str = ""
    id: int | None = field(default=None)
    account_name: str = field(default="")

    # Common income categories
    INCOME_CATEGORIES: list[str] = field(default_factory=lambda: [
        "Salary", "Freelance", "Business", "Investment", "Gift", "Other"
    ], repr=False)

    # Common expense categories
    EXPENSE_CATEGORIES: list[str] = field(default_factory=lambda: [
        "Food & Dining", "Transport", "Housing", "Utilities",
        "Healthcare", "Entertainment", "Shopping", "Education", "Other"
    ], repr=False)

    def __post_init__(self):
        if self.type not in ("income", "expense"):
            raise ValueError(f"Transaction type must be 'income' or 'expense', got '{self.type}'")
        if self.amount <= 0:
            raise ValueError(f"Transaction amount must be positive, got {self.amount}")

    @staticmethod
    def income_categories() -> list[str]:
        return ["Salary", "Freelance", "Business", "Investment", "Gift", "Other"]

    @staticmethod
    def expense_categories() -> list[str]:
        return [
            "Food & Dining", "Transport", "Housing", "Utilities",
            "Healthcare", "Entertainment", "Shopping", "Education", "Other"
        ]
