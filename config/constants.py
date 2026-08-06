"""
Global system constants, keyword sets, and prompt templates.
"""

SYSTEM_KEYWORDS = {
    "battery", "cpu", "ram", "memory status", "disk", "storage",
    "system status", "temperature", "performance", "how's my",
    "how is my", "system info", "system health",
}

FILE_SEARCH_KEYWORDS = {
    "find", "search for", "locate", "where is", "look for", "find my",
}

FILE_NOUNS = {
    "file", "document", "presentation", "pdf", "folder",
    "spreadsheet", "image", "photo", "video", "project",
    "report", "assignment", "notes", "slide",
}

FILE_CONTENT_KEYWORDS = {
    "search inside", "grep", "find in files", "search contents",
    "search within", "look inside", "search in files", "inside",
}

FILE_READ_KEYWORDS = {
    "read this file", "read file", "contents of", "what are the contents of",
    "summarize pdf", "summarize file", "summarize this file", "summarize document",
    "explain document", "explain this document", "what is inside", "read pdf",
    "read document", "explain section", "explain this file", "summarize it",
    "read it", "explain it", "read this", "read document", "summarize", "explain", "read",
    "send", "show", "get", "print", "extract", "display",
}

REMINDER_KEYWORDS = {
    "remind me", "set reminder", "notify me", "alert me",
    "set a reminder", "reminder",
}

OPEN_KEYWORDS = {"open", "launch", "start"}

RUN_KEYWORDS = {"run", "execute", "run command", "shell"}

# ── Memory Subsystem Keywords ────────────────────────────────

MEMORY_STATS_KEYWORDS = {
    "what do you remember", "show my memories", "memory summary",
    "memory stats", "memory statistics", "list everything you know",
    "what is in your memory", "show stored memories",
}

MEMORY_LIST_KEYWORDS = {
    "list memories", "list recent memories", "show recent conversations",
}

MEMORY_SEARCH_KEYWORDS = {
    "search memory for", "search in memory for", "look up in memory",
    "find in memory",
}

MEMORY_EXPORT_KEYWORDS = {
    "export memory", "export all conversations", "export conversations",
    "send me everything", "download memory",
}

MEMORY_DELETE_KEYWORDS = {
    "forget", "delete memory about", "remove memory about", "delete memory",
    "remove memory", "forget that",
}

MEMORY_CLEAR_KEYWORDS = {
    "clear memory", "reset memory", "delete all memories", "delete everything you know",
    "wipe memory", "clear all memories",
}

MEMORY_SUMMARIZE_KEYWORDS = {
    "summarize what you know", "summarize memory", "summarize conversations",
    "summarize everything about", "summarize my recent",
}

SYSTEM_PROMPT = (
    "You are Nexa, a personal desktop assistant with persistent memory. "
    "You run locally on the user's machine. "
    "When given real-time data or tool outputs in the context, "
    "use it to answer naturally in plain language — don't just repeat raw numbers or lists. "
    "For example, say 'Your battery is looking good at 82%' instead of 'Battery: 82%'. "
    "Keep responses concise, conversational, and helpful."
)
