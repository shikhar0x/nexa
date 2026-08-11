from dataclasses import dataclass, field
from typing import Any
import re

from config.constants import (
    SYSTEM_INFO_KEYWORDS,
    PROCESS_KEYWORDS,
    DIRECTORY_LISTING_KEYWORDS,
    FILE_SEARCH_KEYWORDS,
    FILE_NOUNS,
    FILE_CONTENT_KEYWORDS,
    FILE_READ_KEYWORDS,
    REMINDER_KEYWORDS,
    OPEN_KEYWORDS,
    RUN_KEYWORDS,
    KNOWN_SHELL_COMMANDS,
    MEMORY_STATS_KEYWORDS,
    MEMORY_LIST_KEYWORDS,
    MEMORY_SEARCH_KEYWORDS,
    MEMORY_EXPORT_KEYWORDS,
    MEMORY_DELETE_KEYWORDS,
    MEMORY_CLEAR_KEYWORDS,
    MEMORY_SUMMARIZE_KEYWORDS,
    BRIGHTNESS_KEYWORDS,
    VOLUME_KEYWORDS,
    WIFI_KEYWORDS,
    POWER_KEYWORDS,
)
from config.logger import logger


@dataclass
class IntentResult:
    """Data transfer object representing classified intent and extracted arguments."""
    intent_name: str
    args: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class BaseIntentClassifier:
    """Abstract base class interface for intent classifiers."""
    def classify(self, user_input: str) -> IntentResult:
        raise NotImplementedError


AMBIGUOUS_FILE_READ_KEYWORDS = {
    "explain", "summarize", "read", "show", "get", "print", "extract", "display"
}


def _match_kw(kw: str, text: str) -> bool:
    """Check if keyword matches as a distinct whole phrase using regex word boundaries."""
    pattern = rf"\b{re.escape(kw)}\b"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def _match_any(keywords: set[str] | list[str], text: str) -> bool:
    """Check if any keyword in the set matches text using whole-word regex boundaries."""
    return any(_match_kw(kw, text) for kw in keywords)


class IntentRouter(BaseIntentClassifier):
    """Decoupled intent classifier mapping user text to IntentResult objects."""

    def classify(self, user_input: str) -> IntentResult:
        text = user_input.lower().strip()


        # ── 1. Power Control (Safety critical system control) ──────
        if _match_any(POWER_KEYWORDS, text):
            action = "shutdown"
            if any(_match_kw(w, text) for w in ("restart", "reboot")):
                action = "restart"
            elif any(_match_kw(w, text) for w in ("sleep", "hibernate")):
                action = "sleep"
            res = IntentResult(
                intent_name="POWER_CONTROL",
                args={"action": action, "delay": 60},
            )
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 2. Memory Subsystem Operations ───────────────────────
        if _match_any(MEMORY_CLEAR_KEYWORDS, text):
            res = IntentResult(intent_name="MEMORY_CLEAR")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_EXPORT_KEYWORDS, text):
            res = IntentResult(intent_name="MEMORY_EXPORT")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_SUMMARIZE_KEYWORDS, text):
            query = text
            for k in MEMORY_SUMMARIZE_KEYWORDS:
                query = re.sub(rf"\b{re.escape(k)}\b", "", query, flags=re.IGNORECASE)
            res = IntentResult(
                intent_name="MEMORY_SUMMARIZE",
                args={"query": query.strip()},
            )
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_DELETE_KEYWORDS, text):
            query = text
            for k in MEMORY_DELETE_KEYWORDS:
                query = re.sub(rf"\b{re.escape(k)}\b", "", query, flags=re.IGNORECASE)
            res = IntentResult(
                intent_name="MEMORY_DELETE",
                args={"query": query.strip()},
            )
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_SEARCH_KEYWORDS, text):
            query = text
            for k in MEMORY_SEARCH_KEYWORDS:
                query = re.sub(rf"\b{re.escape(k)}\b", "", query, flags=re.IGNORECASE)
            res = IntentResult(
                intent_name="MEMORY_SEARCH",
                args={"query": query.strip()},
            )
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_STATS_KEYWORDS, text):
            res = IntentResult(intent_name="MEMORY_STATS")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(MEMORY_LIST_KEYWORDS, text):
            res = IntentResult(intent_name="MEMORY_LIST")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 3. Shell Command Priority (Check BEFORE semantic status/file intents) ─
        run_res = self._detect_run_command(text, user_input)
        if run_res:
            logger.debug(f"Classified '{user_input}' -> {run_res}")
            return run_res

        # ── 4. Device Controls (Brightness, Volume, Wi-Fi) ────────
        if _match_any(BRIGHTNESS_KEYWORDS, text):
            digits = re.findall(r"\d+", text)
            if digits:
                level = int(digits[0])
                action = "set"
            elif any(_match_kw(w, text) for w in ("set", "dim", "brighten", "change")):
                level = 50
                action = "set"
            else:
                action = "get"
                level = None
            args = {"action": action}
            if level is not None:
                args["level"] = level
            res = IntentResult(intent_name="BRIGHTNESS_CONTROL", args=args)
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(VOLUME_KEYWORDS, text):
            if _match_kw("unmute", text):
                res = IntentResult(intent_name="VOLUME_CONTROL", args={"action": "unmute"})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            elif _match_kw("mute", text):
                res = IntentResult(intent_name="VOLUME_CONTROL", args={"action": "mute"})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

            digits = re.findall(r"\d+", text)
            if digits:
                level = int(digits[0])
                action = "set"
            elif any(_match_kw(w, text) for w in ("set", "turn up", "turn down", "change")):
                level = 50
                action = "set"
            else:
                action = "get"
                level = None
            args = {"action": action}
            if level is not None:
                args["level"] = level
            res = IntentResult(intent_name="VOLUME_CONTROL", args=args)
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(WIFI_KEYWORDS, text):
            if any(_match_kw(w, text) for w in ("list", "available", "scan")):
                action = "list"
            elif any(_match_kw(w, text) for w in ("turn on", "enable", "wifi on")):
                action = "on"
            elif any(_match_kw(w, text) for w in ("turn off", "disable", "wifi off")):
                action = "off"
            elif _match_kw("connect", text):
                action = "connect"
            else:
                action = "status"
            res = IntentResult(intent_name="WIFI_CONTROL", args={"action": action})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 5. Process Info Query ─────────────────────────────────
        if _match_any(PROCESS_KEYWORDS, text):
            res = IntentResult(intent_name="PROCESS_INFO")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 6. Directory Listing Query ─────────────────────────────
        known_folders = ("downloads", "desktop", "documents", "pictures", "music", "videos", "templates", "public")
        is_dir_query = (
            _match_any(DIRECTORY_LISTING_KEYWORDS, text)
            or any(f"in {f}" in text or f"inside {f}" in text or f"show {f}" in text or f"open {f}" in text for f in known_folders)
            or bool(re.search(r"\b(list|show|view|display|count|how many)\b.*\b(in|inside|folder|directory)\b", text))
        )
        if is_dir_query:
            path = self._extract_directory_path(user_input)
            res = IntentResult(intent_name="DIRECTORY_LISTING", args={"path": path})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 7. System Info Query ──────────────────────────────────
        if _match_any(SYSTEM_INFO_KEYWORDS, text):
            res = IntentResult(intent_name="SYSTEM_INFO")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 8. File Operations (Read, Content Search, Open, Search) ─

        has_file_path = bool(re.search(r"(\b~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b[a-zA-Z0-9_\-./]+\.(?:pdf|txt|md|py|js|ts|json|csv|html|css|cpp|c|java))\b", text))
        for kw in FILE_READ_KEYWORDS:
            if _match_kw(kw, text):
                extracted_path = self._extract_path(user_input, kw)
                if kw in AMBIGUOUS_FILE_READ_KEYWORDS and not has_file_path and extracted_path not in ("active_file",):
                    continue
                res = IntentResult(
                    intent_name="FILE_READ",
                    args={"path": extracted_path},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        for kw in FILE_CONTENT_KEYWORDS:
            if _match_kw(kw, text):
                query, target_file = self._extract_content_search_args(user_input, kw)
                res = IntentResult(
                    intent_name="FILE_CONTENT_SEARCH",
                    args={"query": query, "target_file": target_file},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        for kw in REMINDER_KEYWORDS:
            if _match_kw(kw, text):
                delay, message = self._parse_reminder(text)
                res = IntentResult(
                    intent_name="SET_REMINDER",
                    args={"delay_seconds": delay, "message": message},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        for kw in OPEN_KEYWORDS:
            if text.startswith(kw + " "):
                path = self._extract_directory_path(user_input[len(kw):].strip())
                res = IntentResult(
                    intent_name="DIRECTORY_LISTING" if path in ("Downloads", "Desktop", "Documents", "Pictures", "Music", "Videos") else "OPEN_FILE",
                    args={"path": path},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        for kw in FILE_SEARCH_KEYWORDS:
            if _match_kw(kw, text):
                query = self._extract_file_query(text, kw)
                if query:
                    res = IntentResult(
                        intent_name="FILE_SEARCH",
                        args={"query": query},
                    )
                    logger.debug(f"Classified '{user_input}' -> {res}")
                    return res

        if any(_match_kw(noun, text) for noun in FILE_NOUNS):
            for kw in ("find", "where", "locate", "search", "look"):
                if _match_kw(kw, text):
                    query = self._extract_file_query(text, kw)
                    if query:
                        res = IntentResult(
                            intent_name="FILE_SEARCH",
                            args={"query": query},
                        )
                        logger.debug(f"Classified '{user_input}' -> {res}")
                        return res

        # Fallback intent
        res = IntentResult(intent_name="GENERAL")
        logger.debug(f"Classified '{user_input}' -> {res}")
        return res

    def _detect_run_command(self, text: str, user_input: str) -> IntentResult | None:
        """Detect explicit shell command execution requests or known CLI binary invocations."""
        # 1. Prefix triggers in RUN_KEYWORDS (e.g., "run intel_gpu_top", "execute git status")
        for kw in RUN_KEYWORDS:
            if text.startswith(kw + " "):
                cmd = user_input[len(kw):].strip()
                if cmd.lower().startswith("command "):
                    cmd = cmd[len("command "):].strip()
                if cmd:
                    return IntentResult(intent_name="RUN_COMMAND", args={"command": cmd})

        # 2. First word is a known CLI tool or executable script (e.g. "intel_gpu_top", "nvidia-smi", "python main.py")
        words = text.split()
        if not words:
            return None

        first_word = words[0].rstrip(";:,")

        # Exclude ambiguous conversational prefixes if any
        if first_word in ("do", "shell", "exec") and len(words) > 1 and words[1] in ("you", "i", "we", "the", "a", "this"):
            return None

        # Distinguish natural-language "find" queries from explicit shell "find" commands
        if first_word == "find":
            is_shell_find = False
            if len(words) > 1:
                arg1 = words[1].strip("'\"")
                # Shell find paths: ".", "/", "~", "..", or relative/absolute path syntax
                if arg1 in (".", "/", "~", "..") or arg1.startswith(("./", "/", "~/", "../")):
                    is_shell_find = True
                # Shell find flags: -name, -iname, -type, -maxdepth, -exec, etc.
                elif any(w.startswith("-") for w in words[1:]):
                    is_shell_find = True

            if not is_shell_find:
                return None

            return IntentResult(intent_name="RUN_COMMAND", args={"command": user_input.strip()})

        # Distinguish natural-language "grep" queries from explicit shell "grep" commands
        if first_word == "grep":
            is_shell_grep = False
            if len(words) > 1:
                if any(w.startswith("-") for w in words[1:]):
                    is_shell_grep = True
                elif any(w.startswith(("./", "/", "~/", "../")) or "." in w for w in words[2:]):
                    is_shell_grep = True

            if not is_shell_grep:
                return None

            return IntentResult(intent_name="RUN_COMMAND", args={"command": user_input.strip()})

        if first_word in KNOWN_SHELL_COMMANDS or first_word.endswith((".py", ".sh", ".bin", ".pl")):
            return IntentResult(intent_name="RUN_COMMAND", args={"command": user_input.strip()})

        return None



    def _extract_directory_path(self, text: str) -> str:
        """Robust directory path extraction supporting standard user folders and prepositional phrases."""
        # Match explicit paths like /path, ~/path, home/path, ./path
        match = re.search(r"(?:^|\s)['\"]?(~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b\./[^\s,'\"]+)['\"]?", text)
        if match:
            path = match.group(1).strip().strip("'\"")
            if path.startswith("home/"):
                path = "/" + path
            return path

        text_clean = text.strip().rstrip(".").strip("'\"")
        text_lower = text_clean.lower()

        # Check for standard known user folder names
        known_folders = {
            "downloads": "Downloads",
            "desktop": "Desktop",
            "documents": "Documents",
            "pictures": "Pictures",
            "music": "Music",
            "videos": "Videos",
            "templates": "Templates",
            "public": "Public",
        }
        for kw, canonical in known_folders.items():
            if re.search(rf"\b{kw}\b", text_lower):
                return canonical

        # Preposition/trigger based extraction ("in", "inside", "of", "folder", "directory")
        match_prep = re.search(
            r"\b(?:in|inside|of|folder|directory|inside of)\s+['\"]?([a-zA-Z0-9_\-./]+)['\"]?",
            text_clean,
            flags=re.IGNORECASE,
        )
        if match_prep:
            candidate = match_prep.group(1).strip().strip("'\"")
            if candidate.lower() not in ("my", "the", "a", "an", "this", "that"):
                return candidate

        # Strip action & filler words
        filler_patterns = [
            r"^(?:list\s+files\s+in|list\s+directory\s+in|list\s+folder\s+in|list\s+files\s+inside|list\s+pdfs\s+in|list\s+files|list\s+folder|list|show\s+contents\s+of\s+folder|show\s+contents\s+of|show\s+everything\s+inside|show\s+files\s+in|show|open|how\s+many\s+files\s+are\s+in)\s+",
            r"\b(?:in|inside|folder|directory|files|pdfs|everything|all|my|the|a|an)\b",
        ]
        candidate = text_clean
        for pat in filler_patterns:
            candidate = re.sub(pat, " ", candidate, flags=re.IGNORECASE)

        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate.startswith("home/"):
            candidate = "/" + candidate
        return candidate or "workspace"

    def _extract_path(self, text: str, trigger_keyword: str) -> str:
        # Match path starting with /, ~/, home/, or standard filenames, stripping quotes
        match = re.search(r"(?:^|\s)['\"]?(~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)['\"]?", text)
        if match:
            path = match.group(1).strip().strip("'\"")
            if path.startswith("home/"):
                path = "/" + path
            return path

        # Check for pronouns or generic nouns pointing to workspace active file
        text_lower = text.lower()
        if any(p in text_lower for p in (
            "this file", "it", "this document", "that document", "that file",
            "the pdf", "this pdf", "the file", "the document", "the report",
        )):
            return "active_file"

        # Stripped text after trigger
        clean = text
        for kw in FILE_READ_KEYWORDS:
            clean = re.sub(re.escape(kw), "", clean, flags=re.IGNORECASE)

        clean_path = clean.strip().strip("'\"")
        if clean_path.startswith("home/"):
            clean_path = "/" + clean_path
        return clean_path

    def _extract_content_search_args(self, text: str, trigger_keyword: str) -> tuple[str, str]:
        target_file = ""
        path_match = re.search(r"inside\s+['\"]?(~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)['\"]?", text, re.IGNORECASE)
        if path_match:
            target_file = path_match.group(1).strip().strip("'\"")
            if target_file.startswith("home/"):
                target_file = "/" + target_file
        elif "inside this file" in text.lower() or "inside it" in text.lower() or "insid ethe file" in text.lower():
            target_file = "active_file"

        clean = text
        for kw in FILE_CONTENT_KEYWORDS:
            clean = re.sub(re.escape(kw), "", clean, flags=re.IGNORECASE)

        clean = re.sub(r"for\s+the\s+word\s+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"for\s+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"inside\s+.*", "", clean, flags=re.IGNORECASE)

        return clean.strip().strip("'\""), target_file

    def _extract_file_query(self, text: str, trigger_keyword: str) -> str:
        from skills.file_search import normalize_file_query
        return normalize_file_query(text)


    def _parse_reminder(self, text: str) -> tuple[int, str]:
        time_match = re.search(
            r"in\s+(\d+)\s*(seconds?|minutes?|mins?|hours?|hrs?)", text
        )

        delay = 60
        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2).lower()
            if unit.startswith("min"):
                delay = amount * 60
            elif unit.startswith("hour") or unit.startswith("hr"):
                delay = amount * 3600
            else:
                delay = amount

        msg_match = re.search(r"\bto\s+(.+)", text)
        message = msg_match.group(1).strip() if msg_match else "Reminder from Nexa"
        return delay, message
