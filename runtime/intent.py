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
    TIME_DATE_KEYWORDS,
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

# Repo indexing / project summary phrases (developer-mode project overview).
# Kept specific ("this project", "the repo", "codebase") so generic words like
# "project" alone never hijack unrelated queries.
REPO_INDEX_KEYWORDS = (
    "index this repo", "index the repo", "index my repo",
    "index this project", "index the project", "index my project",
    "index this codebase", "index the codebase",
    "what does this project do", "what does the project do", "what does my project do",
    "what does this repo do", "what does the repo do", "what does this codebase do",
    "what is this project", "what's this project", "what is the project about",
    "what is this repo", "what's this repo", "what is this codebase",
    "explain this project", "explain the project", "explain my project",
    "explain this repo", "explain the repo", "explain my repo",
    "explain this codebase", "explain the codebase",
    "summarize this project", "summarize the project", "summarize my project",
    "summarize this repo", "summarize the repo", "summarize this codebase",
    "summarise this project", "summarise this repo",
    "project overview", "repo overview", "codebase overview",
    "project structure", "repo structure", "codebase structure",
    "analyze this project", "analyze the project", "analyze this repo",
    "analyse this project", "analyse this repo",
    "scan this project", "scan this repo", "scan the repo",
    "tell me about this project", "tell me about the project", "tell me about this repo",
    "walk me through this project", "walk me through this repo", "walk me through the codebase",
    "entry point", "tech stack",
)


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
            elif any(_match_kw(w, text) for w in ("sleep", "hibernate", "suspend")):
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

        # ── 2c. Build-Log / Error Analysis ──────────────
        if _match_any(("explain this error", "explain the error", "explain the build error", "what does this error mean", "why did the build fail", "why did the test fail", "explain the traceback", "what went wrong", "explain this log", "explain the log", "what does this log mean", "error in", "read the log", "show me the error"), text):
            import re as _re5
            log_path = ""
            m = _re5.search(r"['\"]?((?:~?/|home/|\./)[^'\"]+)['\"]?", user_input)
            if m:
                log_path = m.group(1).strip()
            res = IntentResult(intent_name="BUILD_LOG", args={"path": log_path})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 2b. Git Queries (BEFORE shell commands) ────────────
        if not text.startswith(("run ", "execute ", "run command ")):
            if _match_any(("git status", "repo status", "repo clean", "repo dirty", "is my repo", "working tree", "uncommitted"), text) or ("what branch" in text) or ("which branch" in text):
                res = IntentResult(intent_name="GIT_STATUS")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("git branch", "list branches", "list all branches"), text):
                res = IntentResult(intent_name="GIT_BRANCH")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("git diff", "show changes", "what changed", "uncommitted changes", "what did i change"), text):
                res = IntentResult(intent_name="GIT_DIFF")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("git log", "recent commits", "commit history", "last commits", "recent history"), text):
                res = IntentResult(intent_name="GIT_LOG")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("git add and commit", "add and commit", "stage and commit", "git add commit", "git commit all"), text):
                # Extract message with prefix-stripping
                msg = text
                prefixes = ("git add and commit", "add and commit", "stage and commit",
                            "git add commit", "git commit all", "git add", "commit")
                changed = True
                while changed:
                    changed = False
                    for prefix in prefixes:
                        if msg.startswith(prefix):
                            msg = msg[len(prefix):].lstrip(" :\"'")
                            changed = True
                            break
                msg = msg.strip().strip("\"'")
                res = IntentResult(intent_name="GIT_ADD_COMMIT", args={"message": msg})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            # Stage-only add. Placed AFTER add-and-commit so "git add and commit"
            # keeps winning; the trailing regex catches "add <paths> to git".
            if _match_any(("git add", "add to git", "git stage", "stage these files", "stage this file",
                           "stage the files", "stage my changes", "track these files", "track this file",
                           "add everything to git", "add all my changes"), text) \
                    or re.search(r"\badd\b[\w\s,'\"|.+-]*?\bto git\b", text):
                add_paths = re.findall(
                    r"(?:~?/[^\s,'\"|]+|\./[^\s,'\"|]+|[a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_.\-]+)+|[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)",
                    user_input,
                )
                res = IntentResult(intent_name="GIT_ADD", args={"paths": add_paths})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("commit ", "git commit"), text):
                import re as _re3
                msg = ""
                m = _re3.search(r"(?:with message|message|commit)\s*['\"]?([^'\"]+)['\"]?$", text)
                if m:
                    msg = m.group(1).strip()
                res = IntentResult(intent_name="GIT_COMMIT", args={"message": msg})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res
            if _match_any(("git checkout", "switch to branch", "switch branch", "checkout branch"), text):
                import re as _re4
                br = ""
                m = _re4.search(r"(?:checkout|switch to)\s+(?:branch\s+)?['\"]?([a-zA-Z0-9_\-/]+)['\"]?", text)
                if m:
                    br = m.group(1).strip()
                res = IntentResult(intent_name="GIT_CHECKOUT", args={"branch": br})
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 2d. Repo Indexing / Project Summary ─────────────
        if _match_any(REPO_INDEX_KEYWORDS, text):
            m = re.search(r"['\"]?((?:~?/|home/|\./)[^'\"]+)['\"]?", user_input)
            repo_path = m.group(1).strip() if m else ""
            res = IntentResult(intent_name="REPO_INDEX", args={"path": repo_path})
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
            elif any(_match_kw(w, text) for w in ("crank", "up", "brighter", "brighten", "increase", "raise", "max", "full")):
                level = 60
                action = "set"
            elif any(_match_kw(w, text) for w in ("dim", "down", "dimmer", "decrease", "lower", "too bright", "reduce", "less bright", "not so bright")):
                level = 40
                action = "set"
            elif any(_match_kw(w, text) for w in ("set", "change")):
                level = 50
                action = "set"
            else:
                action = "get"
                level = None
            args: dict[str, Any] = {"action": action}
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
            elif any(_match_kw(w, text) for w in ("up", "louder", "increase", "raise", "max", "full", "too quiet")):
                level = 60
                action = "set"
            elif any(_match_kw(w, text) for w in ("down", "quieter", "decrease", "lower", "too loud", "reduce", "less loud", "not so loud")):
                level = 40
                action = "set"
            elif any(_match_kw(w, text) for w in ("set", "change")):
                level = 50
                action = "set"
            else:
                action = "get"
                level = None
            args: dict[str, Any] = {"action": action}
            if level is not None:
                args["level"] = level
            res = IntentResult(intent_name="VOLUME_CONTROL", args=args)
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        if _match_any(WIFI_KEYWORDS, text):
            if any(_match_kw(w, text) for w in ("list", "available", "scan")):
                action = "list"
            elif any(_match_kw(w, text) for w in ("turn on", "enable", "wifi on", "switch on")):
                action = "on"
            elif any(_match_kw(w, text) for w in ("turn off", "disable", "wifi off", "kill", "switch off", "disconnect")):
                action = "off"
            elif _match_kw("connect", text):
                action = "connect"
            else:
                action = "status"
            res = IntentResult(intent_name="WIFI_CONTROL", args={"action": action})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 5. Process Info Query ─────────────────────────────────
        is_process_query = _match_any(PROCESS_KEYWORDS, text) or (
            _match_any(("eating", "eats", "eat", "hogging", "hogs", "using", "consuming", "draining", "drains"), text)
            and _match_any(("ram", "memory", "cpu"), text)
        )
        if is_process_query:
            res = IntentResult(intent_name="PROCESS_INFO")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 6. Directory Listing Query ─────────────────────────────
        known_folders = ("downloads", "desktop", "documents", "pictures", "music", "videos", "templates", "public")
        is_dir_query = (
            _match_any(DIRECTORY_LISTING_KEYWORDS, text)
            or any(f"in {f}" in text or f"inside {f}" in text or f"show {f}" in text or f"open {f}" in text or f"search {f}" in text for f in known_folders)
            or bool(re.search(r"\b(list|show|view|display|count|how many)\b.*\b(in|inside|folder|directory)\b", text))
            or text in ("search this folder", "search that folder", "search folder", "list this folder", "list that folder")
        )
        # "What's in THIS FILE" is a file-read query, not a directory listing
        is_dir_query = is_dir_query and not bool(
            re.search(r"\b(this|that|the|a|an) (file|document|pdf|report)\b", text)
        )
        if is_dir_query:
            path = self._extract_directory_path(user_input)
            res = IntentResult(intent_name="DIRECTORY_LISTING", args={"path": path})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 6b. Path Question ("what is '/path/file'?") -> FILE_READ ──
        path_question = re.search(r"(?:what|what's|whats|tell me about|describe)\s+(?:is|are|about)?\s*['\"]?((?:~?/|home/|\./)[^'\"]+)['\"]?\??", user_input, re.IGNORECASE)
        if path_question:
            q_path = path_question.group(1).strip().strip("'\"")
            if q_path.lower().startswith("home/"):
                q_path = "/" + q_path
            res = IntentResult(intent_name="FILE_READ", args={"path": q_path})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 6d. Time & Date Query ──────────────
        if _match_any(TIME_DATE_KEYWORDS, text):
            res = IntentResult(intent_name="TIME_DATE")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 7. System Info Query ──────────────────────────────────
        if _match_any(SYSTEM_INFO_KEYWORDS, text):
            res = IntentResult(intent_name="SYSTEM_INFO", args={"query": user_input})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 8. File Operations (Read, Content Search, Open, Search) ─

        has_file_path = bool(re.search(r"(\b~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b[a-zA-Z0-9_\-./]+\.(?:pdf|docx|doc|txt|md|py|js|ts|json|csv|html|css|cpp|c|java))\b", text))
        for kw in FILE_READ_KEYWORDS:
            if _match_kw(kw, text):
                extracted_path, search_path_hint = self._extract_file_read_args(user_input, kw)
                # "explain it"/"summarize it" with no file noun and no real path
                # is a conversational follow-up -> GENERAL, not a file read error.
                if (
                    not has_file_path
                    and extracted_path == "active_file"
                    and not any(_match_kw(noun, text) for noun in FILE_NOUNS)
                ):
                    continue
                if kw in AMBIGUOUS_FILE_READ_KEYWORDS and not has_file_path and extracted_path not in ("active_file",):
                    continue
                args = {"path": extracted_path}
                if search_path_hint:
                    args["search_path"] = search_path_hint
                res = IntentResult(
                    intent_name="FILE_READ",
                    args=args,
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

        # ── 9b. Memory Date Recall ("what did I do yesterday?") ──
        if _match_any(("yesterday", "what did i do", "what did we do", "what did i talk about", "what did we talk about", "on monday", "on tuesday", "on wednesday", "on thursday", "on friday", "on saturday", "on sunday", "last week", "on the"), text):
            from datetime import date, timedelta
            target = date.today() - timedelta(days=1)
            if "yesterday" not in text:
                import re as _re2
                day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
                day_match = _re2.search(r"\b(mon|tue|wed|thu|fri|sat|sun)\w*\b", text)
                date_match = _re2.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
                if date_match:
                    target = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                elif day_match:
                    today_wd = date.today().weekday()
                    target_wd = day_map[day_match.group(1)[:3]]
                    delta = (today_wd - target_wd) % 7
                    if delta == 0:
                        delta = 7
                    target = date.today() - timedelta(days=delta)
            res = IntentResult(intent_name="MEMORY_DATE", args={"date": target.isoformat()})
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # ── 10. Screenshot ───────────────
        if _match_any(("screenshot", "screen capture", "capture screen", "capture the screen", "snapshot", "take a picture of the screen", "screen shot"), text):
            res = IntentResult(intent_name="SCREENSHOT")
            logger.debug(f"Classified '{user_input}' -> {res}")
            return res

        # Fallback intent
        res = IntentResult(intent_name="GENERAL")
        logger.debug(f"Classified '{user_input}' -> {res}")
        return res

    def extract_args(self, intent_name: str, user_input: str) -> dict[str, Any]:
        """
        Deterministic argument extraction for a given intent, using the same
        extractors as classify(). Used by the hybrid classifier so that an
        LLM-suggested intent still receives args extracted by the trusted
        keyword/regex logic (never by the model).
        """
        text = user_input.lower().strip()

        if intent_name == "DIRECTORY_LISTING":
            return {"path": self._extract_directory_path(user_input)}

        if intent_name == "FILE_READ":
            extracted_path, search_path_hint = self._extract_file_read_args(user_input, "read")
            args = {"path": extracted_path}
            if search_path_hint:
                args["search_path"] = search_path_hint
            return args

        if intent_name == "FILE_CONTENT_SEARCH":
            query, target_file = self._extract_content_search_args(user_input, "search inside")
            return {"query": query, "target_file": target_file}

        if intent_name == "FILE_SEARCH":
            return {"query": self._extract_file_query(text, "find")}

        if intent_name == "SET_REMINDER":
            delay, message = self._parse_reminder(text)
            return {"delay_seconds": delay, "message": message}

        if intent_name == "BRIGHTNESS_CONTROL":
            digits = re.findall(r"\d+", text)
            if digits:
                return {"action": "set", "level": int(digits[0])}
            if any(_match_kw(w, text) for w in ("crank", "up", "brighter", "brighten", "increase", "raise", "max", "full")):
                return {"action": "set", "level": 60}
            if any(_match_kw(w, text) for w in ("dim", "down", "dimmer", "decrease", "lower", "too bright", "reduce")):
                return {"action": "set", "level": 40}
            if any(_match_kw(w, text) for w in ("set", "change")):
                return {"action": "set", "level": 50}
            return {"action": "get"}

        if intent_name == "VOLUME_CONTROL":
            if _match_kw("unmute", text):
                return {"action": "unmute"}
            if _match_kw("mute", text):
                return {"action": "mute"}
            digits = re.findall(r"\d+", text)
            if digits:
                return {"action": "set", "level": int(digits[0])}
            if any(_match_kw(w, text) for w in ("up", "louder", "increase", "raise", "max", "full", "too quiet")):
                return {"action": "set", "level": 60}
            if any(_match_kw(w, text) for w in ("down", "quieter", "decrease", "lower", "too loud", "reduce")):
                return {"action": "set", "level": 40}
            if any(_match_kw(w, text) for w in ("set", "change")):
                return {"action": "set", "level": 50}
            return {"action": "get"}

        if intent_name == "MEMORY_SEARCH":
            query = text
            for k in MEMORY_SEARCH_KEYWORDS:
                query = re.sub(rf"\b{re.escape(k)}\b", "", query, flags=re.IGNORECASE)
            return {"query": query.strip()}

        if intent_name == "MEMORY_SUMMARIZE":
            query = text
            for k in MEMORY_SUMMARIZE_KEYWORDS:
                query = re.sub(rf"\b{re.escape(k)}\b", "", query, flags=re.IGNORECASE)
            return {"query": query.strip()}

        if intent_name == "OPEN_FILE":
            return {"path": self._extract_directory_path(user_input)}

        if intent_name == "REPO_INDEX":
            m = re.search(r"['\"]?((?:~?/|home/|\./)[^'\"]+)['\"]?", user_input)
            return {"path": m.group(1).strip().strip("'\"") if m else ""}

        # SYSTEM_INFO / PROCESS_INFO / MEMORY_STATS / MEMORY_LIST take no args
        return {}

    def _detect_run_command(self, text: str, user_input: str) -> IntentResult | None:
        """Detect explicit shell command execution requests or known CLI binary invocations."""
        # 1. Prefix triggers in RUN_KEYWORDS (e.g., "run intel_gpu_top", "execute git status")
        for kw in RUN_KEYWORDS:
            if text.startswith(kw + " "):
                cmd = user_input[len(kw):].strip()
                if cmd.lower().startswith("command "):
                    cmd = cmd[len("command "):].strip()
                if cmd:
                    # Exclude ambiguous conversational prefixes ("do you ...", "do i ...",
                    # "shell out ...") so natural language is not treated as a command.
                    words_after = cmd.lower().split()
                    if kw in ("do", "shell", "exec") and words_after and words_after[0] in (
                        "you", "i", "we", "the", "a", "an", "this", "that",
                        "it", "they", "my", "your", "our", "me",
                    ):
                        continue
                    # "do X" only fires when X is an actual command, not a noun phrase
                    if kw == "do" and words_after:
                        first = words_after[0].rstrip(";:,")
                        looks_like_command = (
                            first in KNOWN_SHELL_COMMANDS
                            or first.endswith((".py", ".sh", ".bin", ".pl"))
                            or first.startswith(("-", "/", "./", "~/"))
                        )
                        if not looks_like_command:
                            continue
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
                else:
                    # "grep <pattern> in <file>" is natural language content search;
                    # a dotted path BEFORE any "in/inside" connector means a shell grep.
                    connector_idx = next((i for i, w in enumerate(words[1:], start=1) if w in ("in", "inside")), None)
                    if connector_idx is None:
                        is_shell_grep = any(w.startswith(("./", "/", "~/", "../")) or "." in w for w in words[1:])
                    else:
                        is_shell_grep = any(w.startswith(("./", "/", "~/", "../")) or "." in w for w in words[1:connector_idx])

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

    def _extract_file_read_args(self, text: str, trigger_keyword: str) -> tuple[str, str | None]:
        """Extract target file path and optional search path hint (e.g. 'from Downloads' or 'in Documents')."""
        search_hint = None
        raw_hint = None
        from_match = re.search(
            r"\b(?:from|in|inside|inside of)\s+(['\"]?(?:downloads|desktop|documents|pictures|music|videos|templates|public|home|~?/[^\s,'\"]+)['\"]?)",
            text,
            flags=re.IGNORECASE,
        )
        if from_match:
            raw_hint = from_match.group(1).strip().strip("'\"")
            from skills.path_resolver import expand_special_folder
            special = expand_special_folder(raw_hint)
            if special:
                search_hint = special.name
            else:
                search_hint = raw_hint

        path = self._extract_path(text, trigger_keyword)
        if raw_hint and path:
            # Strip 'from <search_hint>' from path if present
            path = re.sub(rf"\b(?:from|in|inside|inside of)\s+{re.escape(raw_hint)}\b", "", path, flags=re.IGNORECASE).strip()

        return path, search_hint

    def _extract_path(self, text: str, trigger_keyword: str) -> str:
        # 1. Quoted paths may contain spaces: '.../Math Report.pdf' or ".../My File.txt"
        quoted = re.search(r"['\"]((?:~?/|home/|\./)[^'\"]+)['\"]", text)
        if quoted:
            path = quoted.group(1).strip()
            if path.startswith("home/"):
                path = "/" + path
            return path

        # 2. Unquoted paths: absolute, home-relative, or standard filenames (no spaces)
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
        path_match = re.search(r"(?:inside|in)\s+['\"]?(~?/[^\s,'\"]+|\bhome/[^\s,'\"]+|\b[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)['\"]?", text, re.IGNORECASE)
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
        clean = re.sub(r"\b(?:inside|in)\s+.*", "", clean, flags=re.IGNORECASE)

        return clean.strip().strip("'\""), target_file

    def _extract_file_query(self, text: str, trigger_keyword: str) -> str:
        from skills.file_search import normalize_file_query
        return normalize_file_query(text)


    def _parse_reminder(self, text: str) -> tuple[int, str]:
        time_match = re.search(
            r"(?:in|for|after)\s+(\d+)\s*(seconds?|minutes?|mins?|hours?|hrs?)", text
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
