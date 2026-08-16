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
    # Tracks which messages have already been embedded into ChromaDB,
    # enabling lazy vector sync (no per-turn embedding cost).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_embeddings (
            msg_id INTEGER PRIMARY KEY
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


def count_messages(db_path: str | None = None) -> int:
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    cur = conn.execute("SELECT COUNT(*) FROM messages")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_recent_messages(limit: int = 2, db_path: str | None = None) -> list[str]:
    """Return the N most recent message contents in chronological order."""
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    cur = conn.execute(
        "SELECT content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
    )
    contents = [r[0] for r in cur.fetchall()][::-1]
    conn.close()
    return contents


def get_unembedded_messages(db_path: str | None = None) -> list[tuple[int, str]]:
    """Return (id, content) for messages not yet embedded into ChromaDB."""
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    cur = conn.execute(
        "SELECT id, content FROM messages "
        "WHERE id NOT IN (SELECT msg_id FROM memory_embeddings) ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_embedded(msg_ids: list[int], db_path: str | None = None) -> None:
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.executemany(
        "INSERT OR IGNORE INTO memory_embeddings (msg_id) VALUES (?)",
        [(i,) for i in msg_ids],
    )
    conn.commit()
    conn.close()


def remove_embedded(msg_ids: list[int], db_path: str | None = None) -> None:
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.executemany(
        "DELETE FROM memory_embeddings WHERE msg_id = ?",
        [(i,) for i in msg_ids],
    )
    conn.commit()
    conn.close()


def clear_embedded(db_path: str | None = None) -> None:
    path = db_path or settings.db_path
    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM memory_embeddings")
    conn.commit()
    conn.close()
