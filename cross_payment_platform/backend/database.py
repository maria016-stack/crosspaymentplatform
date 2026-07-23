"""
Lightweight SQLite persistence layer (no ORM, kept simple and dependency-free).
Stores users, their settings, and their transaction/recommendation history.
"""
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "data", "app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            display_name TEXT,
            phone TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            default_transaction_type TEXT DEFAULT 'Mobile Money Transfer',
            default_location TEXT DEFAULT 'Dar es Salaam',
            email_savings_reports INTEGER DEFAULT 1,
            peak_hour_alerts INTEGER DEFAULT 1,
            sms_alerts INTEGER DEFAULT 0,
            language TEXT DEFAULT 'English',
            date_format TEXT DEFAULT 'DD/MM/YYYY',
            theme TEXT DEFAULT 'Light',
            privacy_mode INTEGER DEFAULT 0,
            data_retention_days INTEGER DEFAULT 90,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TEXT,
            amount REAL,
            transaction_type TEXT,
            location TEXT,
            recommended_platform TEXT,
            pri_score REAL,
            fee REAL,
            speed_seconds INTEGER,
            savings REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password: str, salt: str = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return digest, salt


def create_user(username, email, password, display_name=None):
    conn = get_conn()
    cur = conn.cursor()
    pw_hash, salt = hash_password(password)
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, salt, display_name, phone, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, email, pw_hash, salt, display_name or username, "", datetime.utcnow().isoformat()),
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def verify_password(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    pw_hash, _ = hash_password(password, user["salt"])
    if pw_hash == user["password_hash"]:
        return user
    return None


def get_settings(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def update_settings(user_id, **kwargs):
    if not kwargs:
        return
    conn = get_conn()
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    conn.execute(f"UPDATE settings SET {cols} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def add_transaction(user_id, amount, transaction_type, location, recommended_platform,
                     pri_score, fee, speed_seconds, savings):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO transactions
           (user_id, created_at, amount, transaction_type, location, recommended_platform,
            pri_score, fee, speed_seconds, savings)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, datetime.utcnow().isoformat(), amount, transaction_type, location,
         recommended_platform, pri_score, fee, speed_seconds, savings),
    )
    conn.commit()
    tx_id = cur.lastrowid
    conn.close()
    return tx_id


def get_transactions(user_id, limit=200):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def clear_transactions(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_monthly_savings(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(savings), 0) as total, COALESCE(AVG(pri_score), 0) as avg_pri "
        "FROM transactions WHERE user_id = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row)
