import chromadb
from config.settings import settings
from config.logger import logger

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        logger.debug(f"Initializing ChromaDB client at path '{settings.chroma_path}'")
        _client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = _client.get_or_create_collection(name="nexa_memory")
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