"""
views/settings.py
User settings view: currency, theme, date format, default account, change password.
"""

from __future__ import annotations

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from database import db
from utils.platform_utils import ui_font


# Available currencies: (display label, symbol, name)
CURRENCIES = [
    ("US Dollar       $",  "$",  "US Dollar"),
    ("Euro            €",  "€",  "Euro"),
    ("British Pound   £",  "£",  "British Pound"),
    ("Japanese Yen    ¥",  "¥",  "Japanese Yen"),
    ("Nigerian Naira  ₦",  "₦",  "Nigerian Naira"),
    ("Indian Rupee    ₹",  "₹",  "Indian Rupee"),
    ("Swiss Franc     Fr", "Fr", "Swiss Franc"),
    ("Canadian Dollar C$", "C$", "Canadian Dollar"),
    ("Australian Dol. A$", "A$", "Australian Dollar"),
    ("South African   R",  "R",  "South African Rand"),
    ("Ghanaian Cedi   GH₵", "GH₵", "Ghanaian Cedi"),
]

# Available themes (ttkbootstrap dark / light themes)
THEMES = [
    ("darkly",    "Dark — Darkly"),
    ("cyborg",    "Dark — Cyborg"),
    ("vapor",     "Dark — Vapor"),
    ("superhero", "Dark — Superhero"),
    ("solar",     "Dark — Solar"),
    ("flatly",    "Light — Flatly"),
    ("litera",    "Light — Litera"),
    ("minty",     "Light — Minty"),
    ("pulse",     "Light — Pulse"),
    ("united",    "Light — United"),
    ("yeti",      "Light — Yeti"),
    ("sandstone", "Light — Sandstone"),
]

# Available date formats: (display label, strftime pattern)
DATE_FORMATS = [
    ("Jan 06, 2026       (%b %d, %Y)",  "%b %d, %Y"),
    ("06/01/2026         (%d/%m/%Y)",   "%d/%m/%Y"),
    ("01/06/2026         (%m/%d/%Y)",   "%m/%d/%Y"),
    ("2026-01-06         (%Y-%m-%d)",   "%Y-%m-%d"),
    ("06 January 2026    (%d %B %Y)",   "%d %B %Y"),
    ("Tuesday, Jan 06    (%A, %b %d)",  "%A, %b %d"),
]


class SettingsView(ttkb.Frame):
    """Settings page — persists all changes to the user_settings table."""

    def __init__(self, parent, controller, user_id: int):
        super().__init__(parent)
        self.controller = controller
        self._user_id = user_id
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Scrollable canvas so the page works on smaller screens
        canvas = ttkb.Canvas(self, highlightthickness=0)
        scrollbar = ttkb.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._inner = ttkb.Frame(canvas)
        self._inner_id = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            self._inner_id, width=e.width))

        # Bind mouse-wheel scrolling
        canvas.bind_all("<MouseWheel>",  lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.bind_all("<Button-4>",    lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>",    lambda e: canvas.yview_scroll( 1, "units"))

        self._build_content(self._inner)

    def _build_content(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        ttkb.Label(parent, text="Settings", font=ui_font(18, "bold"),
                   padding=(20, 16)).grid(row=0, column=0, sticky="w")

        # ---- Currency ----
        self._currency_frame = self._make_section(parent, "Currency", row=1)
        self._currency_var = ttkb.StringVar()
        currency_labels = [c[0] for c in CURRENCIES]
        self._currency_combo = ttkb.Combobox(
            self._currency_frame, textvariable=self._currency_var,
            values=currency_labels, state="readonly", width=34)
        self._currency_combo.pack(anchor="w", pady=(4, 0))
        ttkb.Button(self._currency_frame, text="Save Currency",
                    bootstyle="primary-outline",
                    command=self._save_currency).pack(anchor="w", pady=(8, 0))

        # ---- Theme ----
        self._theme_frame = self._make_section(parent, "Theme", row=2)
        self._theme_var = ttkb.StringVar()
        theme_labels = [t[1] for t in THEMES]
        self._theme_combo = ttkb.Combobox(
            self._theme_frame, textvariable=self._theme_var,
            values=theme_labels, state="readonly", width=34)
        self._theme_combo.pack(anchor="w", pady=(4, 0))
        ttkb.Label(self._theme_frame,
                   text="Theme change takes effect immediately.",
                   font=ui_font(8)).pack(anchor="w", pady=(4, 0))
        ttkb.Button(self._theme_frame, text="Apply Theme",
                    bootstyle="primary-outline",
                    command=self._save_theme).pack(anchor="w", pady=(8, 0))

        # ---- Date Format ----
        self._date_frame = self._make_section(parent, "Date Format", row=3)
        self._date_var = ttkb.StringVar()
        date_labels = [d[0] for d in DATE_FORMATS]
        self._date_combo = ttkb.Combobox(
            self._date_frame, textvariable=self._date_var,
            values=date_labels, state="readonly", width=34)
        self._date_combo.pack(anchor="w", pady=(4, 0))
        ttkb.Button(self._date_frame, text="Save Date Format",
                    bootstyle="primary-outline",
                    command=self._save_date_format).pack(anchor="w", pady=(8, 0))

        # ---- Default Account ----
        self._account_frame = self._make_section(parent, "Default Account", row=4)
        ttkb.Label(self._account_frame,
                   text="Pre-selected when adding a new income or expense.",
                   font=ui_font(8)).pack(anchor="w")
        self._default_account_var = ttkb.StringVar()
        self._account_combo = ttkb.Combobox(
            self._account_frame, textvariable=self._default_account_var,
            state="readonly", width=34)
        self._account_combo.pack(anchor="w", pady=(4, 0))
        ttkb.Button(self._account_frame, text="Save Default Account",
                    bootstyle="primary-outline",
                    command=self._save_default_account).pack(anchor="w", pady=(8, 0))

        # ---- Change Password ----
        self._pw_frame = self._make_section(parent, "Change Password", row=5)

        ttkb.Label(self._pw_frame, text="Current Password").pack(anchor="w", pady=(4, 0))
        self._current_pw_var = ttkb.StringVar()
        ttkb.Entry(self._pw_frame, textvariable=self._current_pw_var,
                   show="*", width=36).pack(anchor="w")

        ttkb.Label(self._pw_frame, text="New Password").pack(anchor="w", pady=(8, 0))
        self._new_pw_var = ttkb.StringVar()
        ttkb.Entry(self._pw_frame, textvariable=self._new_pw_var,
                   show="*", width=36).pack(anchor="w")

        ttkb.Label(self._pw_frame, text="Confirm New Password").pack(anchor="w", pady=(8, 0))
        self._confirm_pw_var = ttkb.StringVar()
        ttkb.Entry(self._pw_frame, textvariable=self._confirm_pw_var,
                   show="*", width=36).pack(anchor="w")

        self._pw_status = ttkb.Label(self._pw_frame, text="", font=ui_font(9))
        self._pw_status.pack(anchor="w", pady=(6, 0))

        ttkb.Button(self._pw_frame, text="Change Password",
                    bootstyle="warning-outline",
                    command=self._change_password).pack(anchor="w", pady=(8, 0))

        # Bottom padding
        ttkb.Frame(parent).grid(row=6, column=0, pady=20)

    def _make_section(self, parent, title: str, row: int) -> ttkb.Frame:
        """Create a labelled section card and return its inner frame."""
        outer = ttkb.Frame(parent, padding=(20, 12, 20, 16))
        outer.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 12))
        outer.grid_columnconfigure(0, weight=1)
        ttkb.Label(outer, text=title, font=ui_font(12, "bold")).grid(
            row=0, column=0, sticky="w")
        ttkb.Separator(outer).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        inner = ttkb.Frame(outer)
        inner.grid(row=2, column=0, sticky="ew")
        return inner

    # ------------------------------------------------------------------
    # Refresh — loads saved settings into all controls
    # ------------------------------------------------------------------

    def refresh(self):
        settings = db.get_all_settings(self._user_id)

        # Currency
        saved_symbol = settings.get("currency_symbol", "$")
        for i, (_, symbol, _) in enumerate(CURRENCIES):
            if symbol == saved_symbol:
                self._currency_combo.current(i)
                break

        # Theme
        saved_theme = settings.get("theme", "darkly")
        for i, (key, _) in enumerate(THEMES):
            if key == saved_theme:
                self._theme_combo.current(i)
                break

        # Date format
        saved_fmt = settings.get("date_format", "%b %d, %Y")
        for i, (_, fmt) in enumerate(DATE_FORMATS):
            if fmt == saved_fmt:
                self._date_combo.current(i)
                break

        # Default account — reload account list each time
        accounts = db.get_all_accounts(self._user_id)
        account_names = ["(none)"] + [a["name"] for a in accounts]
        self._account_combo.configure(values=account_names)
        saved_acct = settings.get("default_account", "")
        if saved_acct in account_names:
            self._account_combo.set(saved_acct)
        else:
            self._account_combo.set("(none)")

        # Clear password fields on each visit
        self._current_pw_var.set("")
        self._new_pw_var.set("")
        self._confirm_pw_var.set("")
        self._pw_status.config(text="", bootstyle="default")

    # ------------------------------------------------------------------
    # Save handlers
    # ------------------------------------------------------------------

    def _save_currency(self):
        label = self._currency_var.get()
        match = next((c for c in CURRENCIES if c[0] == label), None)
        if not match:
            return
        db.set_setting(self._user_id, "currency_symbol", match[1])
        db.set_setting(self._user_id, "currency_name",   match[2])
        Messagebox.show_info("Currency saved.", title="Settings")

    def _save_theme(self):
        label = self._theme_var.get()
        match = next((t for t in THEMES if t[1] == label), None)
        if not match:
            return
        theme_key = match[0]
        db.set_setting(self._user_id, "theme", theme_key)
        # Apply immediately
        self.controller.style.theme_use(theme_key)
        Messagebox.show_info("Theme applied.", title="Settings")

    def _save_date_format(self):
        label = self._date_var.get()
        match = next((d for d in DATE_FORMATS if d[0] == label), None)
        if not match:
            return
        db.set_setting(self._user_id, "date_format", match[1])
        Messagebox.show_info("Date format saved.", title="Settings")

    def _save_default_account(self):
        value = self._default_account_var.get()
        db.set_setting(self._user_id, "default_account",
                       "" if value == "(none)" else value)
        Messagebox.show_info("Default account saved.", title="Settings")

    def _change_password(self):
        current  = self._current_pw_var.get()
        new_pw   = self._new_pw_var.get()
        confirm  = self._confirm_pw_var.get()

        if not current or not new_pw or not confirm:
            self._pw_status.config(text="All three fields are required.", bootstyle="danger")
            return
        if len(new_pw) < 8:
            self._pw_status.config(text="New password must be at least 8 characters.", bootstyle="danger")
            return
        if new_pw != confirm:
            self._pw_status.config(text="New passwords do not match.", bootstyle="danger")
            self._confirm_pw_var.set("")
            return

        success = db.change_password(self._user_id, current, new_pw)
        if success:
            self._pw_status.config(text="Password changed successfully.", bootstyle="success")
            self._current_pw_var.set("")
            self._new_pw_var.set("")
            self._confirm_pw_var.set("")
        else:
            self._pw_status.config(text="Current password is incorrect.", bootstyle="danger")
            self._current_pw_var.set("")
