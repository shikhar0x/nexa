import sqlite3
from memory.db import init_db, save_message
from memory.vector_store import add_memory
from memory.retrieval import get_context as retrieve_vector_context
from config.settings import settings
from config.logger import logger


class MemoryService:
    """
    Facade managing conversation logs and persistent vector memory.
    Public API remains stable as underlying storage/fact-extraction evolves.
    """

    def initialize(self) -> None:
        """Initialize underlying databases."""
        logger.info("Initializing MemoryService...")
        init_db()

    def get_context(self, query: str) -> str:
        """Retrieve relevant past context for a given query."""
        context = retrieve_vector_context(query)
        if context:
            logger.debug(f"Retrieved memory context for query '{query}': {len(context)} chars")
        return context

    def store_exchange(self, user_input: str, response: str) -> None:
        """Persist a conversation turn (user prompt + assistant response)."""
        logger.debug(f"Storing turn in SQLite & ChromaDB: '{user_input[:30]}...'")
        save_message("user", user_input)
        user_id = self._get_last_insert_id()
        add_memory(user_input, user_id)

        save_message("assistant", response)
        assist_id = self._get_last_insert_id()
        add_memory(response, assist_id)

    def _get_last_insert_id(self) -> int:
        conn = sqlite3.connect(settings.db_path)
        cur = conn.execute("SELECT last_insert_rowid()")
        result = cur.fetchone()[0]
        conn.close()
        return result
