import chromadb
from config.settings import settings
from config.logger import logger
from memory.db import get_unembedded_messages, mark_embedded

_client = None
_collection = None
_current_path = None


def reset_vector_store():
    """Reset cached ChromaDB client and collection singletons."""
    global _client, _collection, _current_path
    _client = None
    _collection = None
    _current_path = None


def get_collection():
    global _client, _collection, _current_path
    if _collection is None or _current_path != settings.chroma_path:
        logger.debug(f"Initializing ChromaDB client at path '{settings.chroma_path}'")
        if settings.chroma_path == ":memory:":
            _client = chromadb.EphemeralClient()
        else:
            _client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = _client.get_or_create_collection(name="nexa_memory")
        _current_path = settings.chroma_path
    return _collection


def add_memory(text: str, msg_id: int):
    col = get_collection()
    col.add(
        documents=[text],
        ids=[str(msg_id)]
    )


def sync_memory() -> int:
    """
    Lazy vector sync: embed only messages that have not been embedded yet.
    Returns the number of new embeddings created. Runs a single batch add
    so the cost is one-time (after an upgrade or on the first memory query),
    not per conversation turn.
    """
    pending = get_unembedded_messages()
    if not pending:
        return 0

    col = get_collection()
    try:
        # Upgrade-safe: ids embedded before this change may already exist in
        # ChromaDB while the memory_embeddings table is empty.
        existing = set(col.get(include=[])["ids"])
    except Exception as exc:
        logger.warning(f"Could not read existing ChromaDB ids: {exc}")
        existing = set()

    to_add = [(mid, content) for mid, content in pending if str(mid) not in existing]
    if to_add:
        try:
            col.add(
                documents=[content for _, content in to_add],
                ids=[str(mid) for mid, _ in to_add],
            )
        except Exception as exc:
            # Degrade gracefully: memory queries still work, embeddings just
            # aren't updated this round (they will be retried on next sync).
            logger.warning(f"ChromaDB sync failed, embeddings skipped: {exc}")
            return 0

    # Mark ALL pending as embedded (pre-existing ones were embedded before)
    mark_embedded([mid for mid, _ in pending])
    if to_add:
        logger.debug(f"Lazy ChromaDB sync embedded {len(to_add)} new messages")
    return len(to_add)


def search_memory(query: str, top_k: int = 3) -> list[str]:
    try:
        col = get_collection()
        results = col.query(
            query_texts=[query],
            n_results=top_k
        )
    except Exception as exc:
        # Degrade gracefully (same policy as sync_memory): if the embedding
        # backend is unavailable (offline, model not yet downloaded, ChromaDB
        # error), the turn proceeds with no vector memory context instead of
        # crashing the whole request.
        logger.warning(f"ChromaDB query failed, no memory context this turn: {exc}")
        return []
    return results["documents"][0] if results["documents"] else []
