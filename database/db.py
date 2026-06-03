import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'expense_tracker.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    expenses = [
        (user_id, 450.0,  "Food",          "2026-05-01", "Lunch at office"),
        (user_id, 200.0,  "Transport",     "2026-05-03", "Auto rickshaw"),
        (user_id, 1200.0, "Bills",         "2026-05-05", "Electricity bill"),
        (user_id, 500.0,  "Health",        "2026-05-08", "Doctor visit"),
        (user_id, 350.0,  "Entertainment", "2026-05-10", "Movie tickets"),
        (user_id, 800.0,  "Shopping",      "2026-05-15", "Clothes"),
        (user_id, 150.0,  "Other",         "2026-05-18", "Miscellaneous"),
        (user_id, 600.0,  "Food",          "2026-05-20", "Groceries"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()


def create_user(name, email, password_hash):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    db.commit()
    return cursor.lastrowid


def get_user_by_email(email):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    db.close()
    return user


def get_user_by_id(user_id):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    db.close()
    return user


def get_expense_summary(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    by_category = db.execute(
        "SELECT category, SUM(amount) AS subtotal FROM expenses WHERE user_id = ? GROUP BY category ORDER BY subtotal DESC",
        (user_id,)
    ).fetchall()
    db.close()
    return {
        "total": row["total"],
        "count": row["count"],
        "by_category": [(r["category"], r["subtotal"]) for r in by_category],
    }


# ---- History DB Functions ----
def get_user_expenses(user_id, start_date=None, end_date=None):
    db = get_db()
    query = ("SELECT id, amount, category, date, description FROM expenses "
             "WHERE user_id = ?")
    params = [user_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC, id DESC"
    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ---- Summary Stats DB Functions ----
def update_user_profile(user_id, name, email):
    db = get_db()
    db.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (name, email, user_id),
    )
    db.commit()
    db.close()


def update_user_password(user_id, password_hash):
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (password_hash, user_id),
    )
    db.commit()
    db.close()


# ---- Category DB Functions ----
def get_expenses_by_category(user_id, category):
    db = get_db()
    rows = db.execute(
        "SELECT id, amount, date, description FROM expenses "
        "WHERE user_id = ? AND category = ? ORDER BY date DESC, id DESC",
        (user_id, category),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def add_expense(user_id, amount, category, date, description):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    db.close()
    return cursor.lastrowid
