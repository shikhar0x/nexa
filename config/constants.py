"""
Global system constants, keyword sets, and prompt templates.
"""

SYSTEM_KEYWORDS = {
    "battery", "cpu", "ram", "memory", "disk", "storage",
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
    "search within", "look inside", "search in files",
}

REMINDER_KEYWORDS = {
    "remind me", "set reminder", "notify me", "alert me",
    "set a reminder", "reminder",
}

OPEN_KEYWORDS = {"open", "launch", "start"}

RUN_KEYWORDS = {"run", "execute", "run command", "shell"}

SYSTEM_PROMPT = (
    "You are Nexa, a personal desktop assistant with persistent memory. "
    "You run locally on the user's machine. "
    "When given real-time data or tool outputs in the context, "
    "use it to answer naturally in plain language — don't just repeat raw numbers or lists. "
    "For example, say 'Your battery is looking good at 82%' instead of 'Battery: 82%'. "
    "Keep responses concise, conversational, and helpful."
)
