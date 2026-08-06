import sqlite3
import os

from memory.db import init_db, save_message
from memory.vector_store import add_memory, search_memory, get_collection
from memory.retrieval import get_context as retrieve_vector_context
from config.settings import settings
from config.logger import logger


class MemoryService:
    """
    CQRS-aligned facade managing conversation logs and persistent vector memory.
    Public API separates Read Queries from Write Commands and remains stable
    as underlying storage and future Knowledge Extraction evolve.
    """

    def initialize(self) -> None:
        """Initialize underlying databases."""
        logger.info("Initializing MemoryService...")
        init_db()

    # ── Read Queries (CQRS) ──────────────────────────────────────────

    def get_context(self, query: str) -> str:
        """Retrieve relevant past context for prompt injection."""
        context = retrieve_vector_context(query)
        if context:
            logger.debug(f"Retrieved memory context for query '{query}': {len(context)} chars")
        return context

    def get_memory_stats(self) -> dict:
        """Return factual statistics from SQLite and ChromaDB databases."""
        conn = sqlite3.connect(settings.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM messages")
        total_messages = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM messages WHERE role='user'")
        user_messages = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'")
        assistant_messages = cur.fetchone()[0]

        cur.execute("SELECT timestamp FROM messages ORDER BY id ASC LIMIT 1")
        row_oldest = cur.fetchone()
        oldest_date = row_oldest[0].split("T")[0] if row_oldest else "None"

        cur.execute("SELECT timestamp FROM messages ORDER BY id DESC LIMIT 1")
        row_latest = cur.fetchone()
        latest_date = row_latest[0].split("T")[0] if row_latest else "None"

        conn.close()

        # ChromaDB vector count
        col = get_collection()
        vector_count = col.count()

        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "vector_memories": vector_count,
            "oldest_date": oldest_date,
            "latest_date": latest_date,
        }

    def list_recent_memories(self, limit: int = 10) -> list[dict]:
        """List the N most recent logged conversation turns."""
        conn = sqlite3.connect(settings.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()

        return [
            {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def search_memories(self, query: str, top_k: int = 5) -> list[str]:
        """Perform vector search on ChromaDB for memories matching query."""
        return search_memory(query, top_k=top_k)

    def export_conversations(self, output_path: str = "nexa_memory_export.md") -> str:
        """Export raw SQLite conversation log into a clean markdown file."""
        conn = sqlite3.connect(settings.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, role, content, timestamp FROM messages ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()

        lines = [
            "# Nexa Memory Export\n",
            f"**Total Messages:** {len(rows)}\n",
            "---\n",
        ]

        for msg_id, role, content, ts in rows:
            icon = "👤" if role == "user" else "🤖"
            lines.append(f"### {icon} {role.capitalize()} (ID #{msg_id} - {ts})\n\n{content}\n")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported {len(rows)} messages to {output_path}")
        return os.path.abspath(output_path)

    # ── Write Commands (CQRS) ─────────────────────────────────────────

    def store_exchange(self, user_input: str, response: str) -> None:
        """Persist a conversation turn (user prompt + assistant response)."""
        logger.debug(f"Storing turn in SQLite & ChromaDB: '{user_input[:30]}...'")
        save_message("user", user_input)
        user_id = self._get_last_insert_id()
        add_memory(user_input, user_id)

        save_message("assistant", response)
        assist_id = self._get_last_insert_id()
        add_memory(response, assist_id)

    def delete_matching_memories(self, query: str) -> int:
        """Delete messages containing query term from SQLite log and ChromaDB collection."""
        if not query.strip():
            return 0

        conn = sqlite3.connect(settings.db_path)
        cur = conn.cursor()

        # Find matching message IDs
        cur.execute("SELECT id FROM messages WHERE content LIKE ?", (f"%{query}%",))
        matching_ids = [str(r[0]) for r in cur.fetchall()]

        if matching_ids:
            cur.execute("DELETE FROM messages WHERE content LIKE ?", (f"%{query}%",))
            conn.commit()

            # Delete matching IDs from ChromaDB
            col = get_collection()
            try:
                col.delete(ids=matching_ids)
            except Exception as e:
                logger.warning(f"Failed to delete ChromaDB IDs {matching_ids}: {e}")

        conn.close()
        logger.info(f"Deleted {len(matching_ids)} memories matching query '{query}'")
        return len(matching_ids)

    def clear_all_memory(self) -> bool:
        """Wipe SQLite messages table and ChromaDB collection completely."""
        logger.info("Wiping SQLite messages table and ChromaDB persistent store...")
        conn = sqlite3.connect(settings.db_path)
        conn.execute("DELETE FROM messages")
        conn.commit()
        conn.close()

        col = get_collection()
        try:
            # Delete all documents in collection
            existing_ids = col.get()["ids"]
            if existing_ids:
                col.delete(ids=existing_ids)
        except Exception as e:
            logger.warning(f"Error clearing ChromaDB collection: {e}")

        return True

    def _get_last_insert_id(self) -> int:
        conn = sqlite3.connect(settings.db_path)
        cur = conn.execute("SELECT last_insert_rowid()")
        result = cur.fetchone()[0]
        conn.close()
        return result
