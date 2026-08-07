import sqlite3
import re
from config.settings import settings

def init_facts_table():
    conn = sqlite3.connect(settings.db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def set_fact(key: str, value: str):
    conn = sqlite3.connect(settings.db_path)
    conn.execute(
        "INSERT INTO facts (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()

def get_fact(key: str) -> str | None:
    conn = sqlite3.connect(settings.db_path)
    cur = conn.execute("SELECT value FROM facts WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def try_extract_name(user_input: str) -> str | None:
    """Detect explicit 'my name is X' / 'remember my name, it is X' patterns."""
    match = re.search(r"(?:my name is|name,?\s*(?:it'?s|it is))\s+([A-Za-z]+)", user_input, re.IGNORECASE)
    return match.group(1).strip(".,! ") if match else None