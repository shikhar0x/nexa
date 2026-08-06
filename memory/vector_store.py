import chromadb
from config.settings import settings
from config.logger import logger

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


def search_memory(query: str, top_k: int = 3) -> list[str]:
    col = get_collection()
    results = col.query(
        query_texts=[query],
        n_results=top_k
    )
    return results["documents"][0] if results["documents"] else []