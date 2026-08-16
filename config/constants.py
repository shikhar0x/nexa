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
    "battery percentage", "battery health", "battery life",
    "how much battery", "how long will my battery last",
    "what laptop do i have", "what cpu do i have", "what gpu do i have",
    "how much ram do i have", "what are my specs", "tell me my specs",
    "my system", "system model", "what computer do i have",
    "what processor do i have", "laptop model",
}

PROCESS_KEYWORDS = {
    "running processes", "list processes", "top processes", "top cpu",
    "top ram", "cpu hungry", "ram hungry", "process list", "show processes",
    "ps aux", "task manager", "active processes", "process count",
    "list the top cpu-consuming processes", "top cpu consuming processes",
    "eating my ram", "eating my cpu", "what's eating", "whats eating",
    "what is eating", "hogging", "using the most ram", "using the most cpu",
    "uses the most ram", "uses the most cpu", "high cpu usage",
    "high ram usage", "high memory usage", "which process", "what process",
    "my laptop is slow", "my pc is slow", "why is my laptop slow",
    "why is my computer slow", "why is my pc slow", "is my laptop slow",
    "which program is using", "what program is using", "what's using",
    "whats using", "what is using", "using all my ram", "using all my cpu",
    "why is my fan", "fans are spinning", "laptop is hot", "pc is hot",
    "is my laptop hot",
}

DIRECTORY_LISTING_KEYWORDS = {
    "list files in", "list directory", "show contents of folder", "list folder",
    "files in downloads", "files in desktop", "files in documents", "show files in",
    "what files are in", "contents of folder", "contents of directory",
    "show contents of", "list files", "directory listing",
    "show desktop", "show everything inside", "how many files are in",
    "what's in", "whats in", "what is in", "show me what's in",
    "what files do i have", "what's inside", "whats inside", "what is inside",
    "show me the contents of", "what do i have in", "whats in my",
}

FILE_SEARCH_KEYWORDS = {
    "find", "search for", "locate", "where is", "look for", "find my",
    "search for files related to", "got any", "do you have", "any files",
    "any pdfs", "any documents", "any presentations", "where's my",
    "wheres my", "find me", "looking for", "search my files", "show me files",
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
    "which file mentions", "which files mention", "which file contains",
    "which files contain", "where does it mention", "find the file that mentions",
    "find the file containing", "which file has", "which files have",
    "search my documents for", "find the files that mention",
}

FILE_READ_KEYWORDS = {
    "read this file", "read file", "contents of", "what are the contents of",
    "summarize pdf", "summarize file", "summarize this file", "summarize document",
    "explain document", "explain this document", "what is inside", "read pdf",
    "read document", "explain section", "explain this file", "summarize it",
    "read it", "explain it", "read this", "read document", "summarize", "explain", "read",
    "send", "show", "get", "print", "extract", "display",
    "what's in this file", "whats in this file", "what is in this file",
    "what does this file say", "what does this file contain",
    "what is this file", "whats this file", "what's this file",
    "tell me about this file", "what is inside this file",
    "what's inside this file", "whats inside this file",
    "what does this document say", "what is this document",
    "what does this pdf say", "what is this pdf",
}

REMINDER_KEYWORDS = {
    "remind me", "set reminder", "notify me", "alert me",
    "set a reminder", "reminder", "ping me", "set a timer",
    "timer for", "set an alarm", "alarm in", "nudge me",
    "wake me up in", "set a countdown", "countdown for",
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
    "crank", "crank up", "crank the screen", "brightness up", "brightness down",
    "make the screen brighter", "make the screen dimmer", "screen too bright",
    "screen too dim", "too bright", "too dim", "lower the brightness",
    "increase the brightness", "decrease the brightness", "raise the brightness",
    "max brightness", "full brightness", "minimum brightness",
    "brighten the screen", "dim the screen", "brighten the display",
    "dim the display", "turn up brightness", "turn down brightness",
    "make it brighter", "make it dimmer", "less bright", "not so bright",
    "a bit brighter", "a bit dimmer", "little brighter", "little dimmer",
}

VOLUME_KEYWORDS = {
    "volume", "set volume", "turn up volume", "turn down volume",
    "mute", "unmute", "audio volume", "sound volume", "get volume",
    "louder", "quieter", "volume up", "volume down", "make it louder",
    "make it quieter", "turn it up", "turn it down", "raise the volume",
    "lower the volume", "increase the volume", "decrease the volume",
    "max volume", "full volume", "sound up", "sound down", "too loud",
    "too quiet", "raise the sound", "lower the sound", "sound is too low",
    "sound is too high", "less loud", "not so loud",
}

WIFI_KEYWORDS = {
    "wifi", "wi-fi", "wireless", "wifi status", "connect to wifi",
    "turn on wifi", "turn off wifi", "list networks", "available networks",
    "wifi networks", "scan wifi", "kill the wifi", "kill wifi",
    "switch off wifi", "switch on wifi", "disconnect from wifi",
    "wifi not working", "wifi is slow", "can't connect to wifi",
    "cant connect to wifi", "turn wifi", "wifi keeps dropping",
}

POWER_KEYWORDS = {
    "shutdown", "shut down", "restart", "reboot", "sleep", "hibernate",
    "power off", "turn off computer", "turn off pc", "power off the pc",
    "power off the laptop", "shut it down", "shut the pc down",
    "shut the laptop down", "shut the computer down", "power down",
    "power it down", "turn the pc off", "turn the computer off",
    "turn the laptop off", "switch the pc off", "switch the computer off",
    "switch the laptop off",
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
    "\n\nAVAILABLE CAPABILITIES — when asked what you can do, summarize this exact list and nothing else:\n"
    "- System info: battery, CPU, RAM, disk, hardware specs, OS, IP/network details\n"
    "- Running processes: what is using CPU or RAM, why the computer is slow or hot\n"
    "- Files: list folders, find files by name, search inside files, read and summarize documents (PDF, text, code)\n"
    "- Actions (always confirmed first): open files/apps, run shell commands, brightness, volume, wifi, power controls\n"
    "- Reminders and desktop notifications\n"
    "- Persistent memory: stats, list, search, export, delete, clear\n"
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


# ── LLM-Assisted Intent Classification (Hybrid Router) ──────────────
#
# When the deterministic keyword router falls back to GENERAL, the local LLM
# (the SAME single model used for chat) is asked to pick one of these
# capabilities. This dict is BOTH the prompt content and the whitelist:
# anything not listed here can never be suggested by the model.
# Safety-critical intents (POWER_CONTROL, RUN_COMMAND, MEMORY_CLEAR,
# MEMORY_DELETE, MEMORY_EXPORT, WIFI_CONTROL) are intentionally absent —
# they are keyword-router-only and can never be triggered by the LLM.

LLM_CLASSIFIABLE_INTENTS: dict[str, str] = {
    "SYSTEM_INFO": "system health, hardware specs, OS, battery, CPU, RAM, disk, IP or network questions",
    "PROCESS_INFO": "running processes, what is using CPU/RAM, why the computer is slow or hot",
    "DIRECTORY_LISTING": "list or show files/folders in a directory",
    "FILE_SEARCH": "find or search for files by name or topic",
    "FILE_CONTENT_SEARCH": "search inside files for a word or phrase",
    "FILE_READ": "read, summarize, or explain a specific file or document",
    "OPEN_FILE": "open or launch a file or application",
    "SET_REMINDER": "set a reminder, timer, alarm, or notification",
    "BRIGHTNESS_CONTROL": "screen brightness questions or adjustments",
    "VOLUME_CONTROL": "sound volume, mute, or loudness questions",
    "MEMORY_STATS": "what Nexa remembers or its memory statistics",
    "MEMORY_LIST": "recent logged conversations",
    "MEMORY_SEARCH": "search Nexa's stored memories",
    "MEMORY_SUMMARIZE": "summarize what Nexa knows",
    "GENERAL": "everything else: casual chat, opinions, knowledge questions",
}

INTENT_CLASSIFICATION_PROMPT = (
    "You are the intent router of Nexa, a local desktop assistant. "
    "Your ONLY job: choose which single capability matches the user's message.\n\n"
    "Available capabilities:\n"
    + "\n".join(f"- {name}: {desc}" for name, desc in LLM_CLASSIFIABLE_INTENTS.items())
    + "\n\nExamples:\n"
    "- 'what's eating my ram?' -> {\"intent\": \"PROCESS_INFO\"}\n"
    "- 'any pdfs about sql in downloads?' -> {\"intent\": \"FILE_CONTENT_SEARCH\"}\n"
    "- 'crank the screen brightness' -> {\"intent\": \"BRIGHTNESS_CONTROL\"}\n"
    "- 'ping me in 10 minutes' -> {\"intent\": \"SET_REMINDER\"}\n"
    "- 'how much ram do i have' -> {\"intent\": \"SYSTEM_INFO\"}\n"
    "- 'tell me a joke' -> {\"intent\": \"GENERAL\"}\n\n"
    "Reply with STRICT JSON only, no commentary: {\"intent\": \"<CAPABILITY_NAME>\"}"
)
