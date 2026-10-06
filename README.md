# Phantom Finance

A personal finance tracker built with Python and Tkinter.

## Features

- **Dashboard** — summary cards for total income, expenses, and net balance with matplotlib charts
- **Accounts** — create and manage bank, cash, savings, and credit accounts
- **Income** — log and manage income transactions by category
- **Expenses** — log and manage expense transactions by category

## Tech Stack

| Layer     | Library          |
|-----------|------------------|
| UI        | Tkinter + ttkbootstrap |
| Charts    | Matplotlib        |
| Database  | SQLite (stdlib)   |
| Images    | Pillow            |

## Project Structure

```
phantom_finance_tkinter_gui_app/
├── main.py              # Entry point
├── app.py               # Root window & navigation controller
├── requirements.txt
├── views/
│   ├── dashboard.py
│   ├── accounts.py
│   ├── income.py
│   └── expenses.py
├── models/
│   ├── transaction.py
│   └── account.py
├── database/
│   └── db.py            # SQLite init & queries
├── utils/
│   └── helpers.py
└── assets/              # Icons and images
```

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

## Database

SQLite database is stored locally as `phantom_finance.db` in the project root.
It is excluded from version control via `.gitignore`.
