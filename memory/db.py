import sqlite3
from datetime import datetime
from config.settings import settings
from config.logger import logger


def init_db(db_path: str | None = None):
    path = db_path or settings.db_path
    logger.debug(f"Initializing SQLite database at {path}")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(role: str, content: str, db_path: str | None = None):
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()