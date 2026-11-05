# Phantom Finance

A personal finance tracker built with Python and Tkinter.

## Features

- **Dashboard** — summary cards for total income, expenses, and net balance with matplotlib charts
- **Accounts** — create and manage bank, cash, savings, and credit accounts
- **Income** — log and manage income transactions by category
- **Expenses** — log and manage expense transactions by category
- **User settings** — choose a currency (including Ghanaian cedi), theme, date format, and default account; change your password
- **Multi-user** — each user's data is fully isolated; login or register at startup

## Requirements

| Requirement | Version    |
|-------------|------------|
| Python      | 3.9 or newer |
| ttkbootstrap | 1.10.1    |
| matplotlib  | 3.9.4      |
| Pillow      | 11.2.1     |

## Tech Stack

| Layer     | Library               |
|-----------|-----------------------|
| UI        | Tkinter + ttkbootstrap |
| Charts    | Matplotlib (TkAgg)    |
| Database  | SQLite (stdlib)       |
| Images    | Pillow                |

## Project Structure

```
phantom_finance_tkinter_gui_app/
├── main.py              # Entry point
├── app.py               # Root window & navigation controller
├── requirements.txt
├── auth/
│   └── auth.py          # Password hashing (PBKDF2-HMAC-SHA256, stdlib only)
├── views/
│   ├── login.py
│   ├── dashboard.py
│   ├── accounts.py
│   ├── income.py
│   ├── expenses.py
│   └── settings.py
├── models/
│   ├── transaction.py
│   └── account.py
├── database/
│   └── db.py            # SQLite init, migrations & queries
├── utils/
│   ├── helpers.py       # Formatting utilities
│   └── platform_utils.py # OS-aware font and emoji helpers
└── assets/              # Icons and images
```

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (Command Prompt)
.venv\Scripts\Activate.ps1     # Windows (PowerShell)

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

## Platform Notes

### Windows
- Requires Python 3.9+ from [python.org](https://www.python.org/downloads/).
  The Microsoft Store version of Python may have Tkinter limitations — prefer the
  official installer.
- Fonts: uses **Segoe UI** (ships with Windows Vista and later).
- Emoji characters are replaced with plain-text equivalents for compatibility with
  older Tk builds on Windows.

### macOS
- Tkinter on macOS requires a full Python installation (from python.org or Homebrew).
  The system Python shipped with macOS does not include Tkinter.
  ```bash
  brew install python-tk   # if using Homebrew Python
  ```
- Fonts: uses **Helvetica Neue**.
- Charts are rendered at higher DPI automatically on Retina displays.

### Linux
- Tkinter is usually a separate package. Install it if missing:
  ```bash
  sudo apt install python3-tk   # Debian / Ubuntu / Parrot OS
  sudo dnf install python3-tkinter  # Fedora
  ```
- Fonts: uses **DejaVu Sans**.

## Database

SQLite database is stored locally as `phantom_finance.db` in the project root.
It is excluded from version control via `.gitignore`.
The schema is automatically migrated on startup — no manual steps required when
updating from an older version.
