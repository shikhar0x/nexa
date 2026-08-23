"""
Capability index: single source of truth describing every Nexa capability.

The deterministic keyword router (config/constants.py) handles common and
safety-critical phrases. Everything else is routed by the local LLM against
THIS index: the model reads the descriptions and examples, so new phrasings
work WITHOUT editing keyword lists. The index is both the prompt content and
the whitelist — anything not listed here can never be suggested by the model.
"""

CAPABILITY_INDEX: list[dict] = [
    {
        "name": "SYSTEM_INFO",
        "description": "system health, hardware specs, OS, battery, CPU, RAM, disk, IP or network questions",
        "examples": ["how's my battery?", "pc health check", "what cpu do i have", "show os version"],
    },
    {
        "name": "PROCESS_INFO",
        "description": "running processes, what is using CPU/RAM, why the computer is slow or hot",
        "examples": ["what's eating my ram?", "list running processes", "why is my laptop slow"],
    },
    {
        "name": "DIRECTORY_LISTING",
        "description": "list or show files/folders in a directory",
        "examples": ["list files in Downloads", "what's in my documents folder"],
    },
    {
        "name": "FILE_SEARCH",
        "description": "find or search for files by name or topic",
        "examples": ["find my DBMS presentation", "do you have any files about sql"],
    },
    {
        "name": "FILE_CONTENT_SEARCH",
        "description": "search inside files for a word or phrase",
        "examples": ["which files contain sql", "search inside report.pdf for a term"],
    },
    {
        "name": "FILE_READ",
        "description": "read, summarize, or explain a specific file or document",
        "examples": ["summarize report.pdf", "what does this file say"],
    },
    {
        "name": "OPEN_FILE",
        "description": "open or launch a file or application",
        "examples": ["open presentation.pdf", "launch firefox"],
    },
    {
        "name": "SET_REMINDER",
        "description": "set a reminder, timer, alarm, or notification",
        "examples": ["remind me in 10 minutes to stretch", "ping me at 6pm"],
    },
    {
        "name": "BRIGHTNESS_CONTROL",
        "description": "screen brightness questions or adjustments",
        "examples": ["crank the screen brightness", "set brightness to 80%", "screen too bright"],
    },
    {
        "name": "VOLUME_CONTROL",
        "description": "sound volume, mute, or loudness questions",
        "examples": ["make it louder", "mute audio", "volume 70"],
    },
    {
        "name": "MEMORY_STATS",
        "description": "what Nexa remembers or its memory statistics",
        "examples": ["show memory stats", "what do you remember"],
    },
    {
        "name": "MEMORY_LIST",
        "description": "recent logged conversations",
        "examples": ["list recent memories", "show recent conversations"],
    },
    {
        "name": "MEMORY_SEARCH",
        "description": "search Nexa's stored memories",
        "examples": ["search memory for project goals"],
    },
    {
        "name": "MEMORY_SUMMARIZE",
        "description": "summarize what Nexa knows",
        "examples": ["summarize what you know about me"],
    },
    {
        "name": "GIT_STATUS",
        "description": "git repository status, current branch, uncommitted changes, clean/dirty",
        "examples": ["what branch am i on?", "is my repo clean?", "show uncommitted changes"],
    },
    {
        "name": "REPO_INDEX",
        "description": "explain or summarize a code project/repository: what it does, structure, entry point, tech stack",
        "examples": ["what does this project do?", "explain this codebase", "summarize this repo", "index this project"],
    },
    {
        "name": "FILE_WATCH",
        "description": "watch a folder or repo for file changes with desktop notifications; stop or list active watches",
        "examples": ["watch this folder", "keep an eye on this repo", "notify me when files change", "stop watching"],
    },
    {
        "name": "ACTIVE_WINDOW",
        "description": "which application window currently has focus on the desktop",
        "examples": ["what app am i using?", "which window is focused?", "what's the active window?"],
    },
    {
        "name": "WORK_CONTEXT",
        "description": "interpret what the user is currently working on or looking at (richer than just naming the active window)",
        "examples": ["what am i working on?", "what am i doing right now?", "what's in front of me?",
                     "what project am i working on?", "what's the current project?"],
    },
    {
        "name": "GENERAL",
        "description": "everything else: casual chat, opinions, knowledge questions",
        "examples": ["tell me a joke", "what is 2+2?"],
    },
]

# Intents the LLM can NEVER suggest — keyword-router only. A small model
# misfiring must never be able to trigger these on its own.
DESTRUCTIVE_INTENTS: set[str] = {
    "POWER_CONTROL",
    "RUN_COMMAND",
    "MEMORY_CLEAR",
    "MEMORY_DELETE",
    "MEMORY_EXPORT",
    "WIFI_CONTROL",
}
