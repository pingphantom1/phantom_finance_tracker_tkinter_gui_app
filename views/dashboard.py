"""
views/dashboard.py
Dashboard view: summary cards and transaction charts, scoped to the current user.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from database import db
from utils.helpers import format_currency
from utils.platform_utils import ui_font, figure_dpi


class DashboardView(ttkb.Frame):
    """Displays summary stats and charts for the logged-in user's transactions."""

    def __init__(self, parent, controller, user_id: int):
        super().__init__(parent)
        self.controller = controller
        self._user_id = user_id
        self._settings: dict = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ttkb.Label(
            self, text="Dashboard",
            font=ui_font(18, "bold"),
            padding=(20, 16),
        ).grid(row=0, column=0, sticky="w")

        self._cards_frame = ttkb.Frame(self)
        self._cards_frame.grid(row=1, column=0, sticky="ew", padx=20)
        self._cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._income_card  = self._make_card(self._cards_frame, "Total Income",   "$0.00", "success")
        self._expense_card = self._make_card(self._cards_frame, "Total Expenses", "$0.00", "danger")
        self._balance_card = self._make_card(self._cards_frame, "Net Balance",    "$0.00", "info")

        self._income_card.grid( row=0, column=0, padx=(0, 12), sticky="ew")
        self._expense_card.grid(row=0, column=1, padx=(0, 12), sticky="ew")
        self._balance_card.grid(row=0, column=2, sticky="ew")

        self._chart_frame = ttkb.Frame(self)
        self._chart_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=16)
        self.grid_rowconfigure(2, weight=1)

    def _make_card(self, parent, title: str, value: str, style: str) -> ttkb.Frame:
        card = ttkb.Frame(parent, bootstyle=style, padding=16)
        ttkb.Label(card, text=title, font=ui_font(10), bootstyle=f"inverse-{style}").pack(anchor="w")
        value_label = ttkb.Label(card, text=value, font=ui_font(20, "bold"), bootstyle=f"inverse-{style}")
        value_label.pack(anchor="w", pady=(4, 0))
        card._value_label = value_label
        return card

    # ------------------------------------------------------------------
    # Chart rendering
    # ------------------------------------------------------------------

    def _render_charts(self, summary: dict, transactions: list):
        for widget in self._chart_frame.winfo_children():
            widget.destroy()

        dpi = figure_dpi()
        fig = Figure(figsize=(9, 4), dpi=dpi)
        fig.set_layout_engine("tight")
        fig.patch.set_facecolor("#222222")

        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_facecolor("#2b2b2b")
        ax1.bar(
            ["Income", "Expenses"],
            [summary["total_income"], summary["total_expenses"]],
            color=["#28a745", "#dc3545"],
        )
        ax1.set_title("Income vs Expenses", color="white")
        ax1.tick_params(colors="white")
        for spine in ax1.spines.values():
            spine.set_edgecolor("#555")

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.set_facecolor("#2b2b2b")
        expense_rows = [t for t in transactions if t["type"] == "expense"]
        if expense_rows:
            category_totals: dict[str, float] = {}
            for row in expense_rows:
                category_totals[row["category"]] = category_totals.get(row["category"], 0) + row["amount"]
            ax2.pie(
                list(category_totals.values()),
                labels=list(category_totals.keys()),
                autopct="%1.0f%%",
                textprops={"color": "white"},
            )
        else:
            ax2.text(0.5, 0.5, "No expense data yet", ha="center", va="center", color="white")
        ax2.set_title("Expenses by Category", color="white")

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        self._settings = db.get_all_settings(self._user_id)
        summary = db.get_summary(self._user_id)
        transactions = db.get_all_transactions(self._user_id)

        self._income_card._value_label.config(
            text=format_currency(summary["total_income"],   self._settings))
        self._expense_card._value_label.config(
            text=format_currency(summary["total_expenses"], self._settings))
        self._balance_card._value_label.config(
            text=format_currency(summary["net_balance"],    self._settings))

        self._render_charts(summary, transactions)
