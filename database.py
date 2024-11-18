import sqlite3
from datetime import datetime, timedelta
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS authorized_users
                 (user_id INTEGER PRIMARY KEY, expiration_date TEXT)''')
    conn.commit()
    conn.close()

async def is_user_authorized(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT expiration_date FROM authorized_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        expiration_date = datetime.strptime(result[0], "%Y-%m-%d")
        return expiration_date > datetime.now()
    return False

def add_authorized_user(user_id, days):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("INSERT OR REPLACE INTO authorized_users (user_id, expiration_date) VALUES (?, ?)",
              (user_id, expiration_date))
    conn.commit()
    conn.close()

def remove_authorized_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_authorized_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, expiration_date FROM authorized_users")
    users = c.fetchall()
    conn.close()
    return users