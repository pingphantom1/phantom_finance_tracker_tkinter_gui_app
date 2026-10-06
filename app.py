"""
app.py
Root application window and navigation controller.
Manages the sidebar and swaps view frames on navigation.
"""

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from database.db import initialize_db
from views.dashboard import DashboardView
from views.accounts import AccountsView
from views.income import IncomeView
from views.expenses import ExpensesView


class PhantomFinanceApp(ttkb.Window):
    """Main application window with a sidebar navigation and content area."""

    APP_TITLE = "Phantom Finance"
    THEME = "darkly"  # ttkbootstrap theme
    GEOMETRY = "1100x680"

    # Sidebar navigation items: (label, view_class)
    NAV_ITEMS = [
        ("Dashboard",  DashboardView),
        ("Accounts",   AccountsView),
        ("Income",     IncomeView),
        ("Expenses",   ExpensesView),
    ]

    def __init__(self):
        super().__init__(themename=self.THEME)
        self.title(self.APP_TITLE)
        self.geometry(self.GEOMETRY)
        self.minsize(900, 580)

        initialize_db()
        self._frames: dict[str, ttkb.Frame] = {}
        self._build_ui()
        self.show_view("Dashboard")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build sidebar + main content area layout."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

    def _build_sidebar(self):
        """Create the left navigation sidebar."""
        sidebar = ttkb.Frame(self, bootstyle="dark", width=200)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # App title / logo area
        title_label = ttkb.Label(
            sidebar,
            text="💰 Phantom Finance",
            font=("Helvetica", 13, "bold"),
            bootstyle="inverse-dark",
            padding=(16, 20),
        )
        title_label.pack(fill="x")

        ttkb.Separator(sidebar, bootstyle="secondary").pack(fill="x", pady=(0, 8))

        # Navigation buttons
        for label, view_class in self.NAV_ITEMS:
            btn = ttkb.Button(
                sidebar,
                text=label,
                bootstyle="secondary-outline",
                command=lambda lbl=label: self.show_view(lbl),
                width=18,
                padding=(8, 10),
            )
            btn.pack(fill="x", padx=12, pady=4)

    def _build_content_area(self):
        """Create and register all view frames in the content area."""
        container = ttkb.Frame(self)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        for label, view_class in self.NAV_ITEMS:
            frame = view_class(container, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self._frames[label] = frame

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_view(self, name: str):
        """Bring the named view to the front."""
        frame = self._frames.get(name)
        if frame:
            frame.refresh()
            frame.tkraise()
