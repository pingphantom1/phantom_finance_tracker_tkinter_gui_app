"""
views/login.py
Login and registration screen shown before the main app window.
Calls back into the app on successful auth.
"""

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from database import db


class LoginView(ttkb.Frame):
    """
    Full-window login/register screen.
    on_success(user_id) is called when the user authenticates.
    """

    def __init__(self, parent, on_success):
        super().__init__(parent)
        self._on_success = on_success
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Centred card
        card = ttkb.Frame(self, padding=36, bootstyle="dark")
        card.grid(row=0, column=0)

        # App branding
        ttkb.Label(
            card,
            text="💰 Phantom Finance",
            font=("Helvetica", 22, "bold"),
            bootstyle="inverse-dark",
        ).grid(row=0, column=0, columnspan=2, pady=(0, 4))

        ttkb.Label(
            card,
            text="Your personal finance tracker",
            font=("Helvetica", 10),
            bootstyle="inverse-dark",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 24))

        # Notebook for Login / Register tabs
        self._notebook = ttkb.Notebook(card, bootstyle="dark")
        self._notebook.grid(row=2, column=0, columnspan=2, sticky="nsew")

        self._login_tab = ttkb.Frame(self._notebook, padding=16)
        self._register_tab = ttkb.Frame(self._notebook, padding=16)
        self._notebook.add(self._login_tab, text="  Log In  ")
        self._notebook.add(self._register_tab, text="  Register  ")

        self._build_login_tab()
        self._build_register_tab()

    def _build_login_tab(self):
        tab = self._login_tab

        ttkb.Label(tab, text="Username").grid(row=0, column=0, sticky="w", pady=6)
        self._login_user_var = ttkb.StringVar()
        user_entry = ttkb.Entry(tab, textvariable=self._login_user_var, width=30)
        user_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(8, 0))
        user_entry.focus_set()

        ttkb.Label(tab, text="Password").grid(row=1, column=0, sticky="w", pady=6)
        self._login_pass_var = ttkb.StringVar()
        pass_entry = ttkb.Entry(tab, textvariable=self._login_pass_var, show="•", width=30)
        pass_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(8, 0))
        pass_entry.bind("<Return>", lambda _: self._do_login())

        self._login_error = ttkb.Label(tab, text="", bootstyle="danger", font=("Helvetica", 9))
        self._login_error.grid(row=2, column=0, columnspan=2, pady=(4, 0))

        ttkb.Button(
            tab, text="Log In",
            bootstyle="success",
            width=20,
            command=self._do_login,
        ).grid(row=3, column=0, columnspan=2, pady=(14, 0))

    def _build_register_tab(self):
        tab = self._register_tab

        ttkb.Label(tab, text="Username").grid(row=0, column=0, sticky="w", pady=6)
        self._reg_user_var = ttkb.StringVar()
        ttkb.Entry(tab, textvariable=self._reg_user_var, width=30).grid(
            row=0, column=1, sticky="ew", pady=6, padx=(8, 0)
        )

        ttkb.Label(tab, text="Password").grid(row=1, column=0, sticky="w", pady=6)
        self._reg_pass_var = ttkb.StringVar()
        ttkb.Entry(tab, textvariable=self._reg_pass_var, show="•", width=30).grid(
            row=1, column=1, sticky="ew", pady=6, padx=(8, 0)
        )

        ttkb.Label(tab, text="Confirm Password").grid(row=2, column=0, sticky="w", pady=6)
        self._reg_confirm_var = ttkb.StringVar()
        confirm_entry = ttkb.Entry(tab, textvariable=self._reg_confirm_var, show="•", width=30)
        confirm_entry.grid(row=2, column=1, sticky="ew", pady=6, padx=(8, 0))
        confirm_entry.bind("<Return>", lambda _: self._do_register())

        self._reg_error = ttkb.Label(tab, text="", bootstyle="danger", font=("Helvetica", 9))
        self._reg_error.grid(row=3, column=0, columnspan=2, pady=(4, 0))

        ttkb.Button(
            tab, text="Create Account",
            bootstyle="primary",
            width=20,
            command=self._do_register,
        ).grid(row=4, column=0, columnspan=2, pady=(14, 0))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_login(self):
        username = self._login_user_var.get().strip()
        password = self._login_pass_var.get()

        if not username or not password:
            self._login_error.config(text="Please enter your username and password.")
            return

        user_id = db.verify_user(username, password)
        if user_id is None:
            self._login_error.config(text="Invalid username or password.")
            self._login_pass_var.set("")
        else:
            self._login_error.config(text="")
            self._on_success(user_id)

    def _do_register(self):
        username = self._reg_user_var.get().strip()
        password = self._reg_pass_var.get()
        confirm = self._reg_confirm_var.get()

        if not username:
            self._reg_error.config(text="Username cannot be empty.")
            return
        if len(username) < 3:
            self._reg_error.config(text="Username must be at least 3 characters.")
            return
        if len(password) < 8:
            self._reg_error.config(text="Password must be at least 8 characters.")
            return
        if password != confirm:
            self._reg_error.config(text="Passwords do not match.")
            self._reg_confirm_var.set("")
            return

        user_id = db.register_user(username, password)
        if user_id is None:
            self._reg_error.config(text=f"Username '{username}' is already taken.")
        else:
            self._reg_error.config(text="")
            self._on_success(user_id)
