"""
views/accounts.py
Accounts view: list, add, edit, and delete financial accounts for the current user.
"""

from __future__ import annotations

import re
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from database import db
from models.account import Account
from utils.helpers import format_currency, today_str
from utils.platform_utils import ui_font

_DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


class AccountsView(ttkb.Frame):
    """Manage the current user's financial accounts."""

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
        ttkb.Label(header, text="Accounts", font=ui_font(18, "bold")).pack(side="left")
        ttkb.Button(
            header, text="⇄ Transfer",
            bootstyle="info-outline",
            command=self._open_transfer_dialog,
        ).pack(side="right", padx=(8, 0))
        ttkb.Button(
            header, text="+ Add Account",
            bootstyle="success-outline",
            command=self._open_add_dialog,
        ).pack(side="right")

        cols = ("ID", "Name", "Type", "Balance")
        self._tree = ttkb.Treeview(
            self, columns=cols, show="headings",
            bootstyle="info", selectmode="browse",
        )
        for col in cols:
            self._tree.heading(col, text=col)
        self._tree.column("ID",      width=50,  anchor="center")
        self._tree.column("Name",    width=200)
        self._tree.column("Type",    width=120, anchor="center")
        self._tree.column("Balance", width=140, anchor="e")
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
        for row in db.get_all_accounts(self._user_id):
            self._tree.insert("", "end", values=(
                row["id"], row["name"], row["type"],
                format_currency(row["balance"], self._settings),
            ))

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_add_dialog(self):
        default_name = self._settings.get("default_account", "")
        _AccountDialog(self, title="Add Account", on_save=self._save_new_account)

    def _open_edit_dialog(self):
        selected = self._tree.focus()
        if not selected:
            Messagebox.show_warning("Please select an account to edit.", title="No Selection")
            return
        values = self._tree.item(selected, "values")
        account = db.get_account_by_id(int(values[0]), self._user_id)
        if account:
            _AccountDialog(self, title="Edit Account", account=account, on_save=self._save_edit_account)

    def _delete_selected(self):
        selected = self._tree.focus()
        if not selected:
            Messagebox.show_warning("Please select an account to delete.", title="No Selection")
            return
        values = self._tree.item(selected, "values")
        confirm = Messagebox.yesno(
            f"Delete account '{values[1]}'? This cannot be undone.",
            title="Confirm Delete",
        )
        if confirm == "Yes":
            db.delete_account(int(values[0]), self._user_id)
            self.refresh()

    def _save_new_account(self, name: str, account_type: str, balance: float):
        db.insert_account(self._user_id, name, account_type, balance)
        self.refresh()

    def _save_edit_account(self, account_id: int, name: str, account_type: str, balance: float):
        db.update_account(account_id, self._user_id, name, account_type, balance)
        self.refresh()

    def _open_transfer_dialog(self):
        accounts = db.get_all_accounts(self._user_id)
        if len(accounts) < 2:
            Messagebox.show_warning(
                "You need at least two accounts to make a transfer.",
                title="Not Enough Accounts",
            )
            return
        _TransferDialog(self, user_id=self._user_id, accounts=accounts,
                        settings=self._settings, on_done=self.refresh)


# ---------------------------------------------------------------------------
# Account Add / Edit Dialog
# ---------------------------------------------------------------------------

class _AccountDialog(ttkb.Toplevel):
    def __init__(self, parent, title: str, on_save, account=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self._on_save = on_save
        self._account = account
        self._build_form()
        if account:
            self._populate(account)

    def _build_form(self):
        form = ttkb.Frame(self, padding=20)
        form.pack(fill="both", expand=True)

        ttkb.Label(form, text="Account Name").grid(row=0, column=0, sticky="w", pady=4)
        self._name_var = ttkb.StringVar()
        ttkb.Entry(form, textvariable=self._name_var, width=28).grid(row=0, column=1, sticky="ew", pady=4)

        ttkb.Label(form, text="Type").grid(row=1, column=0, sticky="w", pady=4)
        self._type_var = ttkb.StringVar()
        ttkb.Combobox(form, textvariable=self._type_var, values=Account.account_types(), width=26).grid(row=1, column=1, pady=4)

        ttkb.Label(form, text="Opening Balance").grid(row=2, column=0, sticky="w", pady=4)
        self._balance_var = ttkb.StringVar(value="0.00")
        ttkb.Entry(form, textvariable=self._balance_var, width=28).grid(row=2, column=1, sticky="ew", pady=4)

        ttkb.Button(form, text="Save", bootstyle="success", command=self._submit).grid(row=3, column=1, sticky="e", pady=(12, 0))

    def _populate(self, account):
        self._name_var.set(account["name"])
        self._type_var.set(account["type"])
        self._balance_var.set(str(account["balance"]))

    def _submit(self):
        name = self._name_var.get().strip()
        account_type = self._type_var.get().strip()
        try:
            balance = float(self._balance_var.get())
        except ValueError:
            Messagebox.show_error("Balance must be a number.", title="Invalid Input")
            return
        if not name or not account_type:
            Messagebox.show_error("Name and type are required.", title="Invalid Input")
            return
        if len(name) > 60:
            Messagebox.show_error("Account name must be 60 characters or fewer.", title="Invalid Input")
            return
        if self._account:
            self._on_save(self._account["id"], name, account_type, balance)
        else:
            self._on_save(name, account_type, balance)
        self.destroy()


# ---------------------------------------------------------------------------
# Transfer Dialog
# ---------------------------------------------------------------------------

class _TransferDialog(ttkb.Toplevel):
    """Modal dialog for transferring funds between two accounts."""

    def __init__(self, parent, *, user_id: int, accounts, settings: dict, on_done):
        super().__init__(parent)
        self.title("Transfer Funds")
        self.resizable(False, False)
        self._user_id  = user_id
        self._accounts = list(accounts)
        self._settings = settings
        self._on_done  = on_done
        self._build_form()

    def _build_form(self):
        form = ttkb.Frame(self, padding=24)
        form.pack(fill="both", expand=True)

        account_names = [a["name"] for a in self._accounts]

        # From account
        ttkb.Label(form, text="From Account").grid(row=0, column=0, sticky="w", pady=4)
        self._from_var = ttkb.StringVar()
        self._from_combo = ttkb.Combobox(
            form, textvariable=self._from_var,
            values=account_names, state="readonly", width=28,
        )
        self._from_combo.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))
        if account_names:
            self._from_combo.current(0)

        # Balance display for source
        self._from_bal_label = ttkb.Label(form, text="", font=ui_font(8), bootstyle="secondary")
        self._from_bal_label.grid(row=1, column=1, sticky="w", padx=(8, 0))
        self._from_combo.bind("<<ComboboxSelected>>", lambda _: self._update_balance_labels())

        # To account
        ttkb.Label(form, text="To Account").grid(row=2, column=0, sticky="w", pady=(12, 4))
        self._to_var = ttkb.StringVar()
        self._to_combo = ttkb.Combobox(
            form, textvariable=self._to_var,
            values=account_names, state="readonly", width=28,
        )
        self._to_combo.grid(row=2, column=1, sticky="ew", pady=(12, 4), padx=(8, 0))
        if len(account_names) > 1:
            self._to_combo.current(1)
        self._to_bal_label = ttkb.Label(form, text="", font=ui_font(8), bootstyle="secondary")
        self._to_bal_label.grid(row=3, column=1, sticky="w", padx=(8, 0))
        self._to_combo.bind("<<ComboboxSelected>>", lambda _: self._update_balance_labels())

        # Amount
        ttkb.Label(form, text="Amount").grid(row=4, column=0, sticky="w", pady=(12, 4))
        self._amount_var = ttkb.StringVar()
        ttkb.Entry(form, textvariable=self._amount_var, width=30).grid(
            row=4, column=1, sticky="ew", pady=(12, 4), padx=(8, 0))

        # Description (optional)
        ttkb.Label(form, text="Note (optional)").grid(row=5, column=0, sticky="w", pady=4)
        self._note_var = ttkb.StringVar()
        ttkb.Entry(form, textvariable=self._note_var, width=30).grid(
            row=5, column=1, sticky="ew", pady=4, padx=(8, 0))

        # Date
        ttkb.Label(form, text="Date").grid(row=6, column=0, sticky="w", pady=4)
        self._date_var = ttkb.StringVar(value=today_str())
        ttkb.Entry(form, textvariable=self._date_var, width=30).grid(
            row=6, column=1, sticky="ew", pady=4, padx=(8, 0))
        ttkb.Label(form, text="YYYY-MM-DD", font=ui_font(8),
                   bootstyle="secondary").grid(row=7, column=1, sticky="w", padx=(8, 0))

        # Status / error label
        self._status_label = ttkb.Label(form, text="", font=ui_font(9))
        self._status_label.grid(row=8, column=0, columnspan=2, pady=(8, 0))

        # Buttons
        btn_frame = ttkb.Frame(form)
        btn_frame.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttkb.Button(btn_frame, text="Cancel", bootstyle="secondary-outline",
                    command=self.destroy).pack(side="right", padx=(8, 0))
        ttkb.Button(btn_frame, text="Transfer", bootstyle="info",
                    command=self._submit).pack(side="right")

        self._update_balance_labels()

    def _update_balance_labels(self):
        sym = self._settings.get("currency_symbol", "$")
        from_name = self._from_var.get()
        to_name   = self._to_var.get()
        for acct in self._accounts:
            if acct["name"] == from_name:
                self._from_bal_label.config(
                    text=f"Balance: {sym}{acct['balance']:,.2f}")
            if acct["name"] == to_name:
                self._to_bal_label.config(
                    text=f"Balance: {sym}{acct['balance']:,.2f}")

    def _submit(self):
        from_name = self._from_var.get()
        to_name   = self._to_var.get()

        from_acct = next((a for a in self._accounts if a["name"] == from_name), None)
        to_acct   = next((a for a in self._accounts if a["name"] == to_name),   None)

        if not from_acct or not to_acct:
            self._status_label.config(
                text="Please select both accounts.", bootstyle="danger")
            return
        if from_acct["id"] == to_acct["id"]:
            self._status_label.config(
                text="Source and destination must be different accounts.", bootstyle="danger")
            return

        try:
            amount = float(self._amount_var.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            self._status_label.config(
                text="Amount must be a positive number.", bootstyle="danger")
            return

        date = self._date_var.get().strip()
        if not _DATE_RE.match(date):
            self._status_label.config(
                text="Date must be YYYY-MM-DD (e.g. 2026-11-05).", bootstyle="danger")
            return

        note = self._note_var.get().strip()
        if len(note) > 200:
            self._status_label.config(
                text="Note must be 200 characters or fewer.", bootstyle="danger")
            return

        try:
            db.record_transfer(
                self._user_id,
                from_account_id=from_acct["id"],
                to_account_id=to_acct["id"],
                amount=amount,
                description=note,
                date=date,
            )
        except ValueError as exc:
            self._status_label.config(text=str(exc), bootstyle="danger")
            return

        self._on_done()
        self.destroy()
        Messagebox.show_info(
            f"Transferred {self._settings.get('currency_symbol', '$')}{amount:,.2f} "
            f"from {from_name} to {to_name}.",
            title="Transfer Complete",
        )
