"""
views/transactions.py
Full transaction history page with a filter bar.

Defaults to the current calendar month on first load.
Filters: date range, transaction type, account, keyword search.
Supports deleting individual transactions (and full transfer pairs).
"""

from __future__ import annotations

import re
from calendar import monthrange
from datetime import date

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from database import db
from utils.helpers import format_currency, format_date, today_str
from utils.platform_utils import ui_font

_DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

# Treeview column definitions: (id, header label, width, anchor)
_COLUMNS = [
    ("id",          "ID",          52,  "center"),
    ("date",        "Date",        110, "center"),
    ("account",     "Account",     150, "w"),
    ("type",        "Type",        90,  "center"),
    ("category",    "Category",    130, "w"),
    ("description", "Description", 220, "w"),
    ("amount",      "Amount",      120, "e"),
]


def _month_bounds(today: date) -> tuple[str, str]:
    """Return (first day, last day) of today's month as ISO strings."""
    first = today.replace(day=1).isoformat()
    last  = today.replace(day=monthrange(today.year, today.month)[1]).isoformat()
    return first, last


class TransactionsView(ttkb.Frame):
    """All-transactions history page with live filtering."""

    def __init__(self, parent, controller, user_id: int):
        super().__init__(parent)
        self.controller = controller
        self._user_id   = user_id
        self._settings: dict = {}
        # _rows[iid] -> sqlite3.Row for the selected tree item
        self._rows: dict[str, object] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Page header ──────────────────────────────────────────────
        ttkb.Label(self, text="Transactions", font=ui_font(18, "bold"),
                   padding=(20, 16)).grid(row=0, column=0, sticky="w")

        # ── Filter bar ───────────────────────────────────────────────
        self._filter_frame = ttkb.LabelFrame(
            self, text="Filter & Search", padding=(16, 8))
        self._filter_frame.grid(row=1, column=0, sticky="ew",
                                padx=20, pady=(0, 8))
        self._build_filter_bar(self._filter_frame)

        # ── Treeview ─────────────────────────────────────────────────
        tree_frame = ttkb.Frame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 4))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        col_ids = [c[0] for c in _COLUMNS]
        self._tree = ttkb.Treeview(
            tree_frame, columns=col_ids, show="headings",
            bootstyle="primary", selectmode="browse",
        )
        for col_id, label, width, anchor in _COLUMNS:
            self._tree.heading(col_id, text=label,
                               command=lambda c=col_id: self._sort_by(c))
            self._tree.column(col_id, width=width, anchor=anchor, minwidth=40)

        self._tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttkb.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=vsb.set)

        hsb = ttkb.Scrollbar(tree_frame, orient="horizontal",
                             command=self._tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self._tree.configure(xscrollcommand=hsb.set)

        # ── Bottom action bar ─────────────────────────────────────────
        bottom = ttkb.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 12))

        self._count_label = ttkb.Label(bottom, text="", font=ui_font(9),
                                       bootstyle="secondary")
        self._count_label.pack(side="left")

        ttkb.Button(bottom, text="Delete Selected",
                    bootstyle="danger-outline",
                    command=self._delete_selected).pack(side="right")

    def _build_filter_bar(self, parent):
        # Row 0: date range
        ttkb.Label(parent, text="From", font=ui_font(9)).grid(
            row=0, column=0, sticky="w")
        self._date_from_var = ttkb.StringVar()
        ttkb.Entry(parent, textvariable=self._date_from_var,
                   width=13).grid(row=0, column=1, padx=(4, 12), sticky="w")

        ttkb.Label(parent, text="To", font=ui_font(9)).grid(
            row=0, column=2, sticky="w")
        self._date_to_var = ttkb.StringVar()
        ttkb.Entry(parent, textvariable=self._date_to_var,
                   width=13).grid(row=0, column=3, padx=(4, 12), sticky="w")

        ttkb.Label(parent, text="YYYY-MM-DD", font=ui_font(8),
                   bootstyle="secondary").grid(row=0, column=4, sticky="w", padx=(0, 20))

        # Type filter
        ttkb.Label(parent, text="Type", font=ui_font(9)).grid(
            row=0, column=5, sticky="w")
        self._type_var = ttkb.StringVar(value="All")
        type_combo = ttkb.Combobox(
            parent, textvariable=self._type_var,
            values=["All", "Income", "Expense", "Transfer"],
            state="readonly", width=12,
        )
        type_combo.grid(row=0, column=6, padx=(4, 12), sticky="w")

        # Account filter
        ttkb.Label(parent, text="Account", font=ui_font(9)).grid(
            row=0, column=7, sticky="w")
        self._account_var = ttkb.StringVar(value="All Accounts")
        self._account_combo = ttkb.Combobox(
            parent, textvariable=self._account_var,
            state="readonly", width=18,
        )
        self._account_combo.grid(row=0, column=8, padx=(4, 12), sticky="w")

        # Row 1: keyword search
        ttkb.Label(parent, text="Search", font=ui_font(9)).grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        self._keyword_var = ttkb.StringVar()
        ttkb.Entry(parent, textvariable=self._keyword_var,
                   width=40).grid(row=1, column=1, columnspan=5,
                                  padx=(4, 12), pady=(8, 0), sticky="w")
        ttkb.Label(parent, text="searches description & category",
                   font=ui_font(8), bootstyle="secondary").grid(
            row=1, column=6, columnspan=3, sticky="w", pady=(8, 0))

        # Buttons
        btn_frame = ttkb.Frame(parent)
        btn_frame.grid(row=0, column=9, rowspan=2, sticky="e", padx=(16, 0))
        ttkb.Button(btn_frame, text="Apply", bootstyle="primary",
                    command=self._apply_filters).pack(pady=(0, 4), fill="x")
        ttkb.Button(btn_frame, text="This Month", bootstyle="secondary-outline",
                    command=self._reset_to_month).pack(pady=(0, 4), fill="x")
        ttkb.Button(btn_frame, text="Clear", bootstyle="secondary-outline",
                    command=self._clear_filters).pack(fill="x")

        parent.grid_columnconfigure(9, weight=1)

    # ------------------------------------------------------------------
    # Filter logic
    # ------------------------------------------------------------------

    def _reset_to_month(self):
        first, last = _month_bounds(date.today())
        self._date_from_var.set(first)
        self._date_to_var.set(last)
        self._type_var.set("All")
        self._account_var.set("All Accounts")
        self._keyword_var.set("")
        self._load_data()

    def _clear_filters(self):
        self._date_from_var.set("")
        self._date_to_var.set("")
        self._type_var.set("All")
        self._account_var.set("All Accounts")
        self._keyword_var.set("")
        self._load_data()

    def _apply_filters(self):
        # Validate any date entered
        for var, label in ((self._date_from_var, "From date"),
                           (self._date_to_var,   "To date")):
            val = var.get().strip()
            if val and not _DATE_RE.match(val):
                Messagebox.show_error(
                    f"{label} must be YYYY-MM-DD (e.g. 2026-11-05) or left empty.",
                    title="Invalid Date",
                )
                return
        self._load_data()

    def _load_data(self):
        """Fetch rows matching current filter state and populate the tree."""
        date_from = self._date_from_var.get().strip() or None
        date_to   = self._date_to_var.get().strip()   or None
        keyword   = self._keyword_var.get().strip()   or None

        type_sel = self._type_var.get()
        tx_type  = None if type_sel == "All" else type_sel.lower()

        account_name = self._account_var.get()
        account_id   = None
        if account_name != "All Accounts":
            match = next(
                (a for a in self._all_accounts if a["name"] == account_name), None
            )
            if match:
                account_id = match["id"]

        rows = db.get_filtered_transactions(
            self._user_id,
            date_from=date_from,
            date_to=date_to,
            tx_type=tx_type,
            account_id=account_id,
            keyword=keyword,
        )

        self._tree.delete(*self._tree.get_children())
        self._rows.clear()

        for row in rows:
            is_transfer = bool(row["is_transfer"])
            # For display: transfers show their raw type tag plus "(Transfer)"
            if is_transfer:
                type_tag = "Transfer"
                category = "Transfer"
            else:
                type_tag = row["type"].capitalize()
                category = row["category"]

            amount_str = format_currency(row["amount"], self._settings)
            date_str   = format_date(row["date"], self._settings)

            iid = self._tree.insert("", "end", values=(
                row["id"],
                date_str,
                row["account_name"],
                type_tag,
                category,
                row["description"] or "",
                amount_str,
            ))
            self._rows[iid] = row

        n = len(rows)
        self._count_label.config(text=f"{n} transaction{'s' if n != 1 else ''} found")

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    _sort_reverse: dict[str, bool] = {}

    def _sort_by(self, col: str):
        """Toggle sort on the clicked column header."""
        rev = self._sort_reverse.get(col, False)
        items = [(self._tree.set(iid, col), iid)
                 for iid in self._tree.get_children()]
        items.sort(key=lambda x: x[0].lower() if x[0] else "", reverse=rev)
        for idx, (_, iid) in enumerate(items):
            self._tree.move(iid, "", idx)
        self._sort_reverse[col] = not rev

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _delete_selected(self):
        selected = self._tree.focus()
        if not selected:
            Messagebox.show_warning("Select a transaction to delete.",
                                    title="No Selection")
            return

        row = self._rows.get(selected)
        if row is None:
            return

        is_transfer = bool(row["is_transfer"])

        if is_transfer:
            confirm = Messagebox.yesno(
                "This is part of a transfer. Both the debit and credit legs "
                "will be deleted and the account balances will be reversed.\n\n"
                "Continue?",
                title="Delete Transfer",
            )
            if confirm != "Yes":
                return
            # Use the debit side's id regardless of which leg the user clicked
            debit_id = row["debit_tx_id"]
            db.delete_transfer(debit_id, self._user_id)
        else:
            values = self._tree.item(selected, "values")
            confirm = Messagebox.yesno(
                f"Delete this {values[3].lower()} transaction of {values[6]}?",
                title="Confirm Delete",
            )
            if confirm != "Yes":
                return
            db.delete_transaction(row["id"], self._user_id)

        self._load_data()

    # ------------------------------------------------------------------
    # Refresh (called by app.py show_view)
    # ------------------------------------------------------------------

    def refresh(self):
        self._settings = db.get_all_settings(self._user_id)

        # Reload account list for the filter combo
        self._all_accounts = db.get_all_accounts(self._user_id)
        account_names = ["All Accounts"] + [a["name"] for a in self._all_accounts]
        current = self._account_var.get()
        self._account_combo.configure(values=account_names)
        if current not in account_names:
            self._account_var.set("All Accounts")

        # On first visit set the date range to the current month; subsequent
        # visits preserve whatever the user had set.
        if not self._date_from_var.get():
            first, last = _month_bounds(date.today())
            self._date_from_var.set(first)
            self._date_to_var.set(last)

        self._load_data()
