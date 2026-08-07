"""
Global system constants, keyword sets, and prompt templates.
"""

SYSTEM_INFO_KEYWORDS = {
    "battery", "cpu", "ram", "memory status", "disk", "storage",
    "system status", "temperature", "performance", "how's my",
    "how is my", "system info", "system health", "hardware",
    "hardware stats", "hardware specs", "hardware components",
    "specs", "specifications", "system specs", "pc specs",
    "laptop specs", "machine specs", "stats", "system stats",
    "get stats", "show stats", "cpu model", "gpu", "processor",
    "gpu stats", "what specs", "my specs", "hardware info",
    "what do you see", "check specs", "check system", "system state",
    "system details", "component stats", "components",
    "os version", "operating system", "kernel version", "kernel",
    "distro", "ubuntu version", "system os", "hostname", "computer name",
    "uptime", "system uptime", "uname", "ip", "my ip", "what is my ip",
    "what's my ip", "ip address", "local ip", "network ip",
    "network interface", "network interfaces", "gateway", "mac address",
    "netmask", "complete system report", "system report",
    "how long has my computer been running", "how long has my pc been running",
    "how long has the system been running", "how long has it been running",
    "boot time", "linux version", "show my linux version",
    "what operating system am I running", "cpu usage", "system temperature",
}

PROCESS_KEYWORDS = {
    "running processes", "list processes", "top processes", "top cpu",
    "top ram", "cpu hungry", "ram hungry", "process list", "show processes",
    "ps aux", "task manager", "active processes", "process count",
    "list the top cpu-consuming processes", "top cpu consuming processes",
}

DIRECTORY_LISTING_KEYWORDS = {
    "list files in", "list directory", "show contents of folder", "list folder",
    "files in downloads", "files in desktop", "files in documents", "show files in",
    "what files are in", "contents of folder", "contents of directory",
    "show contents of", "list files", "directory listing",
    "show desktop", "show everything inside", "how many files are in",
}

FILE_SEARCH_KEYWORDS = {
    "find", "search for", "locate", "where is", "look for", "find my",
    "search for files related to",
}


FILE_NOUNS = {
    "file", "document", "presentation", "pdf", "folder",
    "spreadsheet", "image", "photo", "video", "project",
    "report", "assignment", "notes", "slide",
}

FILE_CONTENT_KEYWORDS = {
    "search inside", "grep", "find in files", "search contents",
    "search within", "look inside", "search in files", "inside",
    "search for sql inside pdfs", "search sql inside pdfs",
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

RUN_KEYWORDS = {"run", "execute", "run command", "shell", "exec", "bash", "cmd", "do"}

KNOWN_SHELL_COMMANDS = {
    "intel_gpu_top", "nvidia-smi", "python", "python3", "git", "ls", "pwd",
    "cat", "grep", "find", "top", "htop", "fastfetch", "neofetch", "bash",
    "sh", "curl", "wget", "docker", "systemctl", "pip", "npm", "lscpu",
    "lspci", "lsusb", "df", "du", "free", "uname", "uptime", "whoami",
}


# ── Hardware & System Control Keywords ───────────────────────

BRIGHTNESS_KEYWORDS = {
    "brightness", "screen brightness", "set brightness", "dim screen",
    "brighten screen", "change brightness", "get brightness",
}

VOLUME_KEYWORDS = {
    "volume", "set volume", "turn up volume", "turn down volume",
    "mute", "unmute", "audio volume", "sound volume", "get volume",
}

WIFI_KEYWORDS = {
    "wifi", "wi-fi", "wireless", "wifi status", "connect to wifi",
    "turn on wifi", "turn off wifi", "list networks", "available networks",
    "wifi networks", "scan wifi",
}

POWER_KEYWORDS = {
    "shutdown", "shut down", "restart", "reboot", "sleep", "hibernate",
    "power off", "turn off computer", "turn off pc",
}

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
    "wipe memory", "clear all memories", "erase memory", "erase all memory",
    "erase all memories", "erase all the memory", "forget everything",
}


MEMORY_SUMMARIZE_KEYWORDS = {
    "summarize what you know", "summarize memory", "summarize conversations",
    "summarize everything about", "summarize my recent",
}

SYSTEM_PROMPT = (
    "You are Nexa, an intelligent personal desktop AI assistant with persistent memory. "
    "You run locally on the user's Linux (Ubuntu) machine. "
    "CRITICAL REQUIREMENT: Never invent or hallucinate hardware specs or system status numbers. "
    "CRITICAL GROUNDING RULE: Never refer to previous tool outputs, earlier measurements, or conversational history (e.g. NEVER say 'As mentioned earlier', 'According to previous data', or 'Previously'). Answer strictly and independently using the current tool output. "
    "CRITICAL COMMAND RULE: Do NOT suggest or recommend terminal commands (e.g. 'ip addr', 'top', 'htop', 'uptime') if Nexa has already answered the question, UNLESS the user explicitly asks how to do it manually or the capability is unsupported. "
    "Keep responses concise, conversational, and grounded."
)

GROUNDED_INTERPRETATION_PROMPT = (
    "STRICT DATA GROUNDING DIRECTIVES (ALLOW_INTERPRETATION = TRUE):\n"
    "1. The structured tool data below was gathered directly from verified local system tools.\n"
    "2. Explain and interpret these exact values naturally and conversationally (e.g., explaining if CPU/RAM/Disk load is low, moderate, or high).\n"
    "3. NEVER invent, estimate, or hallucinate metrics, frequencies, hardware specs, process lists, or numbers not present in the data.\n"
    "4. ABSOLUTE INDEPENDENCE: Never refer to previous context, earlier measurements, past turns, or prior outputs (e.g. NEVER say 'As mentioned earlier', 'According to previous data', or 'Previously'). Treat each turn as completely independent.\n"
    "5. NO UNNECESSARY COMMANDS: Do NOT recommend terminal commands (e.g., ip addr, top, htop, uptime) if the answer is already provided in the tool output, UNLESS the user explicitly asked for command recommendations or manual instructions.\n"
    "6. EXPLICIT UNAVAILABLE DATA: If any field is marked 'Unavailable (None)', explicitly inform the user that live data for that sensor is not exposed by the current backend.\n"
    "7. NEVER fabricate command outputs, terminal logs, or shell execution results."
)
