"""
app.py
Root application window and navigation controller.
Shows the login screen first; after auth it builds the main UI and
stores the session user_id for all data queries.
"""

from __future__ import annotations

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from database.db import initialize_db, get_username, get_setting
from views.login import LoginView
from views.dashboard import DashboardView
from views.accounts import AccountsView
from views.income import IncomeView
from views.expenses import ExpensesView
from views.transactions import TransactionsView
from views.settings import SettingsView
from utils.platform_utils import ui_font


class PhantomFinanceApp(ttkb.Window):
    """Main application window with a login gate, sidebar navigation, and session management."""

    APP_TITLE = "Phantom Finance"
    DEFAULT_THEME = "darkly"
    # Main window: 3/4 of screen width; height scaled to a 16:9 ratio
    MAIN_WIDTH_RATIO = 0.75
    MAIN_ASPECT = 9 / 16
    # Login window fixed size
    LOGIN_WIDTH = 460
    LOGIN_HEIGHT = 400

    NAV_ITEMS = [
        ("Dashboard",    DashboardView),
        ("Accounts",     AccountsView),
        ("Income",       IncomeView),
        ("Expenses",     ExpensesView),
        ("Transactions", TransactionsView),
        ("Settings",     SettingsView),
    ]

    def __init__(self):
        super().__init__(themename=self.DEFAULT_THEME)
        self.title(self.APP_TITLE)
        self.minsize(460, 380)

        initialize_db()

        self._user_id: int | None = None
        self._frames: dict[str, ttkb.Frame] = {}
        self._sidebar: ttkb.Frame | None = None
        self._username_label: ttkb.Label | None = None

        self._show_login()

    # ------------------------------------------------------------------
    # Login screen
    # ------------------------------------------------------------------

    def _show_login(self):
        """Display the login/register screen, sized as a small centred dialog."""
        self._clear_window()
        self._center_window(self.LOGIN_WIDTH, self.LOGIN_HEIGHT)
        self.minsize(self.LOGIN_WIDTH, self.LOGIN_HEIGHT)

        login_view = LoginView(self, on_success=self._on_login_success)
        login_view.pack(fill="both", expand=True)

    def _on_login_success(self, user_id: int):
        """Called by LoginView after a successful login or registration."""
        self._user_id = user_id
        # Apply the user's saved theme before building the main UI
        saved_theme = get_setting(user_id, "theme")
        if saved_theme:
            self.style.theme_use(saved_theme)
        self._show_main_ui()

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def _show_main_ui(self):
        """Build and display the full app UI after successful login."""
        self._clear_window()

        # Compute window size: 3/4 screen width, height proportional (16:9)
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width  = int(screen_w * self.MAIN_WIDTH_RATIO)
        height = int(width * self.MAIN_ASPECT)
        # Cap height so it always fits on screen with a small margin
        height = min(height, int(screen_h * 0.88))
        min_w, min_h = 900, 580
        self._center_window(max(width, min_w), max(height, min_h))
        self.minsize(min_w, min_h)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()
        self.show_view("Dashboard")

    def _build_sidebar(self):
        """Create the left navigation sidebar with user info and logout."""
        self._sidebar = ttkb.Frame(self, bootstyle="dark", width=200)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)

        # App branding
        ttkb.Label(
            self._sidebar,
            text="Phantom Finance",
            font=ui_font(13, "bold"),
            bootstyle="inverse-dark",
            padding=(16, 16),
        ).pack(fill="x")

        ttkb.Separator(self._sidebar, bootstyle="secondary").pack(fill="x")

        # Logged-in user label
        username = get_username(self._user_id)
        self._username_label = ttkb.Label(
            self._sidebar,
            text=username,
            font=ui_font(9),
            bootstyle="inverse-dark",
            padding=(16, 8),
        )
        self._username_label.pack(fill="x")

        ttkb.Separator(self._sidebar, bootstyle="secondary").pack(fill="x", pady=(0, 8))

        # Navigation buttons (all items except Settings go in the main group)
        for label, _ in self.NAV_ITEMS:
            if label == "Settings":
                continue
            ttkb.Button(
                self._sidebar,
                text=label,
                bootstyle="secondary-outline",
                command=lambda lbl=label: self.show_view(lbl),
                width=18,
                padding=(8, 10),
            ).pack(fill="x", padx=12, pady=4)

        # Spacer pushes the bottom group down
        ttkb.Frame(self._sidebar, bootstyle="dark").pack(fill="both", expand=True)

        # Settings + Logout pinned to the bottom
        ttkb.Separator(self._sidebar, bootstyle="secondary").pack(fill="x", pady=(0, 4))
        ttkb.Button(
            self._sidebar,
            text="Settings",
            bootstyle="secondary-outline",
            command=lambda: self.show_view("Settings"),
            width=18,
            padding=(8, 10),
        ).pack(fill="x", padx=12, pady=(0, 4))
        ttkb.Button(
            self._sidebar,
            text="Log Out",
            bootstyle="danger-outline",
            command=self._logout,
            width=18,
            padding=(8, 10),
        ).pack(fill="x", padx=12, pady=(0, 12))

    def _build_content_area(self):
        """Create and stack all view frames; they receive user_id at construction."""
        container = ttkb.Frame(self)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._frames.clear()
        for label, view_class in self.NAV_ITEMS:
            frame = view_class(container, self, self._user_id)
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[label] = frame

    # ------------------------------------------------------------------
    # Navigation & session
    # ------------------------------------------------------------------

    def show_view(self, name: str):
        """Bring the named view to the front and refresh its data."""
        frame = self._frames.get(name)
        if frame:
            frame.refresh()
            frame.tkraise()

    def _logout(self):
        """Clear the session and return to the login screen."""
        self._user_id = None
        self._frames.clear()
        # Reset to default theme on logout
        self.style.theme_use(self.DEFAULT_THEME)
        self.minsize(self.LOGIN_WIDTH, self.LOGIN_HEIGHT)
        self._show_login()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_window(self):
        """Destroy all child widgets to prepare for a layout swap."""
        for widget in self.winfo_children():
            widget.destroy()
        # Reset grid config
        for col in range(self.grid_size()[0]):
            self.grid_columnconfigure(col, weight=0)
        for row in range(self.grid_size()[1]):
            self.grid_rowconfigure(row, weight=0)

    def _center_window(self, width: int, height: int):
        """Center the window on the screen."""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
