from memory.vector_store import search_memory

def get_context(query):
    relevant = search_memory(query)
    if not relevant:
        return ""
    return "Relevant past context:\n" + "\n".join(f"- {r}" for r in relevant)