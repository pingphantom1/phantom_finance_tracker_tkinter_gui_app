"""
views/income.py
Income view: list, add, edit, and delete income transactions for the current user.
"""

from __future__ import annotations

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from database import db
from models.transaction import Transaction
from utils.helpers import format_currency, format_date, today_str
from utils.platform_utils import ui_font


class IncomeView(ttkb.Frame):
    """Manage income transactions for the logged-in user."""

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

        header = ttkb.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ttkb.Label(header, text="Income", font=ui_font(18, "bold")).pack(side="left")
        ttkb.Button(
            header, text="+ Add Income",
            bootstyle="success-outline",
            command=self._open_add_dialog,
        ).pack(side="right")

        cols = ("ID", "Date", "Account", "Category", "Description", "Amount")
        self._tree = ttkb.Treeview(
            self, columns=cols, show="headings",
            bootstyle="success", selectmode="browse",
        )
        for col in cols:
            self._tree.heading(col, text=col)
        self._tree.column("ID",          width=50,  anchor="center")
        self._tree.column("Date",        width=110, anchor="center")
        self._tree.column("Account",     width=140)
        self._tree.column("Category",    width=140)
        self._tree.column("Description", width=220)
        self._tree.column("Amount",      width=120, anchor="e")
        self._tree.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))

        scrollbar = ttkb.Scrollbar(self, orient="vertical", command=self._tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 8))
        self._tree.configure(yscrollcommand=scrollbar.set)

        btn_row = ttkb.Frame(self)
        btn_row.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 16))
        ttkb.Button(btn_row, text="Edit",   bootstyle="warning-outline", command=self._open_edit_dialog).pack(side="left", padx=4)
        ttkb.Button(btn_row, text="Delete", bootstyle="danger-outline",  command=self._delete_selected).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh(self):
        self._settings = db.get_all_settings(self._user_id)
        self._tree.delete(*self._tree.get_children())
        for row in db.get_transactions_by_type(self._user_id, "income"):
            self._tree.insert("", "end", values=(
                row["id"],
                format_date(row["date"], self._settings),
                row["account_name"],
                row["category"],
                row["description"] or "",
                format_currency(row["amount"], self._settings),
            ))

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_add_dialog(self):
        _TransactionDialog(
            self, title="Add Income", transaction_type="income",
            user_id=self._user_id, settings=self._settings,
            on_save=self._save_new,
        )

    def _open_edit_dialog(self):
        selected = self._tree.focus()
        if not selected:
            Messagebox.show_warning("Please select a transaction to edit.", title="No Selection")
            return
        values = self._tree.item(selected, "values")
        rows = db.get_transactions_by_type(self._user_id, "income")
        row = next((r for r in rows if r["id"] == int(values[0])), None)
        if row:
            _TransactionDialog(
                self, title="Edit Income", transaction_type="income",
                user_id=self._user_id, settings=self._settings,
                transaction=row, on_save=self._save_edit,
            )

    def _delete_selected(self):
        selected = self._tree.focus()
        if not selected:
            Messagebox.show_warning("Please select a transaction to delete.", title="No Selection")
            return
        values = self._tree.item(selected, "values")
        confirm = Messagebox.yesno(
            f"Delete this income entry of {values[5]}?",
            title="Confirm Delete",
        )
        if confirm == "Yes":
            db.delete_transaction(int(values[0]))
            self.refresh()

    def _save_new(self, account_id, category, amount, description, date):
        db.insert_transaction(account_id, "income", category, amount, description, date)
        self.refresh()

    def _save_edit(self, transaction_id, account_id, category, amount, description, date):
        db.update_transaction(transaction_id, account_id, "income", category, amount, description, date)
        self.refresh()


# ---------------------------------------------------------------------------
# Transaction Add / Edit Dialog
# ---------------------------------------------------------------------------

class _TransactionDialog(ttkb.Toplevel):
    def __init__(self, parent, title: str, transaction_type: str,
                 user_id: int, settings: dict, on_save, transaction=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self._type = transaction_type
        self._user_id = user_id
        self._settings = settings
        self._on_save = on_save
        self._transaction = transaction
        self._accounts = db.get_all_accounts(user_id)
        self._build_form()
        if transaction:
            self._populate(transaction)

    def _build_form(self):
        form = ttkb.Frame(self, padding=20)
        form.pack(fill="both", expand=True)

        ttkb.Label(form, text="Account").grid(row=0, column=0, sticky="w", pady=4)
        self._account_var = ttkb.StringVar()
        account_names = [a["name"] for a in self._accounts]
        account_combo = ttkb.Combobox(
            form, textvariable=self._account_var, values=account_names, width=26)
        account_combo.grid(row=0, column=1, pady=4)
        # Pre-select default account if set
        default = self._settings.get("default_account", "")
        if default and default in account_names:
            self._account_var.set(default)

        ttkb.Label(form, text="Category").grid(row=1, column=0, sticky="w", pady=4)
        self._category_var = ttkb.StringVar()
        categories = Transaction.income_categories()
        ttkb.Combobox(form, textvariable=self._category_var, values=categories, width=26).grid(row=1, column=1, pady=4)

        ttkb.Label(form, text="Amount").grid(row=2, column=0, sticky="w", pady=4)
        self._amount_var = ttkb.StringVar()
        ttkb.Entry(form, textvariable=self._amount_var, width=28).grid(row=2, column=1, sticky="ew", pady=4)

        ttkb.Label(form, text="Description").grid(row=3, column=0, sticky="w", pady=4)
        self._desc_var = ttkb.StringVar()
        ttkb.Entry(form, textvariable=self._desc_var, width=28).grid(row=3, column=1, sticky="ew", pady=4)

        ttkb.Label(form, text="Date (YYYY-MM-DD)").grid(row=4, column=0, sticky="w", pady=4)
        self._date_var = ttkb.StringVar(value=today_str())
        ttkb.Entry(form, textvariable=self._date_var, width=28).grid(row=4, column=1, sticky="ew", pady=4)

        ttkb.Button(form, text="Save", bootstyle="success", command=self._submit).grid(
            row=5, column=1, sticky="e", pady=(12, 0))

    def _populate(self, row):
        account = next((a for a in self._accounts if a["id"] == row["account_id"]), None)
        if account:
            self._account_var.set(account["name"])
        self._category_var.set(row["category"])
        self._amount_var.set(str(row["amount"]))
        self._desc_var.set(row["description"] or "")
        self._date_var.set(row["date"])

    def _submit(self):
        account_name = self._account_var.get()
        account = next((a for a in self._accounts if a["name"] == account_name), None)
        if not account:
            Messagebox.show_error("Please select a valid account.", title="Invalid Input")
            return
        category = self._category_var.get().strip()
        date = self._date_var.get().strip()
        description = self._desc_var.get().strip()
        try:
            amount = float(self._amount_var.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            Messagebox.show_error("Amount must be a positive number.", title="Invalid Input")
            return
        if not category or not date:
            Messagebox.show_error("Category and date are required.", title="Invalid Input")
            return
        if self._transaction:
            self._on_save(self._transaction["id"], account["id"], category, amount, description, date)
        else:
            self._on_save(account["id"], category, amount, description, date)
        self.destroy()
