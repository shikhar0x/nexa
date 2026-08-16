from memory.vector_store import search_memory, sync_memory
from memory.db import count_messages, get_recent_messages
from config.settings import settings


def get_context(query):
    """
    Retrieve relevant past context for prompt injection.

    Small-log fast path: below settings.memory_min_messages_for_search the
    vector store is skipped entirely (zero embeddings) and the last few
    turns are returned directly from SQLite instead. Above the threshold,
    pending messages are lazily synced (one-time batch) before searching.
    """
    total = count_messages()
    if total < settings.memory_min_messages_for_search:
        recent = get_recent_messages(limit=settings.memory_context_recent_turns)
        if not recent:
            return ""
        return "Relevant past context:\n" + "\n".join(f"- {r}" for r in recent)

    sync_memory()
    relevant = search_memory(query)
    if not relevant:
        return ""

    lines = [f"- {r}" for r in relevant]
    # Cap injected context length: smaller prompt = faster first token on CPU
    capped = []
    total_chars = 0
    for line in lines:
        if total_chars + len(line) > settings.memory_context_max_chars:
            break
        capped.append(line)
        total_chars += len(line) + 1
    if not capped:
        capped = [lines[0][: settings.memory_context_max_chars]]
    return "Relevant past context:\n" + "\n".join(capped)
