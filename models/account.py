"""
models/account.py
Data class representing a financial account.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Account:
    name: str
    type: str          # 'bank', 'cash', 'credit', 'savings'
    balance: float = 0.0
    id: int | None = field(default=None)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Account name cannot be empty.")

    @staticmethod
    def account_types() -> list[str]:
        return ["Bank", "Cash", "Credit", "Savings", "Investment"]
