from dataclasses import dataclass, field
from typing import Any
import re

from config.constants import (
    SYSTEM_KEYWORDS,
    FILE_SEARCH_KEYWORDS,
    FILE_NOUNS,
    FILE_CONTENT_KEYWORDS,
    REMINDER_KEYWORDS,
    OPEN_KEYWORDS,
    RUN_KEYWORDS,
    MEMORY_STATS_KEYWORDS,
    MEMORY_LIST_KEYWORDS,
    MEMORY_SEARCH_KEYWORDS,
    MEMORY_EXPORT_KEYWORDS,
    MEMORY_DELETE_KEYWORDS,
    MEMORY_CLEAR_KEYWORDS,
    MEMORY_SUMMARIZE_KEYWORDS,
)
from config.logger import logger


@dataclass
class IntentResult:
    """Data transfer object representing classified intent and extracted arguments."""
    intent_name: str
    args: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class IntentRouter:
    """Decoupled intent classifier mapping user text to IntentResult objects."""

    def classify(self, user_input: str) -> IntentResult:
        text = user_input.lower().strip()

        # ── 1. Memory Clear (check before general memory) ─────────
        for kw in MEMORY_CLEAR_KEYWORDS:
            if kw in text:
                res = IntentResult(intent_name="MEMORY_CLEAR")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 2. Memory Export ─────────────────────────────────────
        for kw in MEMORY_EXPORT_KEYWORDS:
            if kw in text:
                res = IntentResult(intent_name="MEMORY_EXPORT")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 3. Memory Summarize (AI reasoning over memory) ───────
        for kw in MEMORY_SUMMARIZE_KEYWORDS:
            if kw in text:
                query = text
                for k in MEMORY_SUMMARIZE_KEYWORDS:
                    query = query.replace(k, "")
                res = IntentResult(
                    intent_name="MEMORY_SUMMARIZE",
                    args={"query": query.strip()},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 4. Memory Delete / Forget ─────────────────────────────
        for kw in MEMORY_DELETE_KEYWORDS:
            if kw in text:
                query = text
                for k in MEMORY_DELETE_KEYWORDS:
                    query = query.replace(k, "")
                res = IntentResult(
                    intent_name="MEMORY_DELETE",
                    args={"query": query.strip()},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 5. Memory Search ─────────────────────────────────────
        for kw in MEMORY_SEARCH_KEYWORDS:
            if kw in text:
                query = text
                for k in MEMORY_SEARCH_KEYWORDS:
                    query = query.replace(k, "")
                res = IntentResult(
                    intent_name="MEMORY_SEARCH",
                    args={"query": query.strip()},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 6. Memory Stats / Summary ────────────────────────────
        for kw in MEMORY_STATS_KEYWORDS:
            if kw in text:
                res = IntentResult(intent_name="MEMORY_STATS")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 7. Memory List ───────────────────────────────────────
        for kw in MEMORY_LIST_KEYWORDS:
            if kw in text:
                res = IntentResult(intent_name="MEMORY_LIST")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 8. System Status ─────────────────────────────────────
        for kw in SYSTEM_KEYWORDS:
            if kw in text:
                res = IntentResult(intent_name="SYSTEM_STATUS")
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 9. File content search ───────────────────────────────
        for kw in FILE_CONTENT_KEYWORDS:
            if kw in text:
                query = text
                for k in FILE_CONTENT_KEYWORDS:
                    query = query.replace(k, "")
                res = IntentResult(
                    intent_name="FILE_CONTENT_SEARCH",
                    args={"query": query.strip()},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 10. Reminder ──────────────────────────────────────────
        for kw in REMINDER_KEYWORDS:
            if kw in text:
                delay, message = self._parse_reminder(text)
                res = IntentResult(
                    intent_name="SET_REMINDER",
                    args={"delay_seconds": delay, "message": message},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 11. Open file ─────────────────────────────────────────
        for kw in OPEN_KEYWORDS:
            if text.startswith(kw + " "):
                path = text[len(kw):].strip()
                if "/" in path or "." in path or any(n in text for n in FILE_NOUNS):
                    res = IntentResult(
                        intent_name="OPEN_FILE",
                        args={"path": user_input[len(kw):].strip()},
                    )
                    logger.debug(f"Classified '{user_input}' -> {res}")
                    return res

        # ── 12. Run command ───────────────────────────────────────
        for kw in RUN_KEYWORDS:
            if text.startswith(kw + " "):
                cmd = user_input[len(kw):].strip()
                if cmd.lower().startswith("command "):
                    cmd = cmd[len("command "):]
                res = IntentResult(
                    intent_name="RUN_COMMAND",
                    args={"command": cmd},
                )
                logger.debug(f"Classified '{user_input}' -> {res}")
                return res

        # ── 13. File search ───────────────────────────────────────
        for kw in FILE_SEARCH_KEYWORDS:
            if kw in text:
                query = self._extract_file_query(text, kw)
                if query:
                    res = IntentResult(
                        intent_name="FILE_SEARCH",
                        args={"query": query},
                    )
                    logger.debug(f"Classified '{user_input}' -> {res}")
                    return res

        if any(noun in text for noun in FILE_NOUNS):
            for kw in ("find", "where", "locate", "search", "look"):
                if kw in text:
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

    def _extract_file_query(self, text: str, trigger_keyword: str) -> str:
        filler_words = {
            trigger_keyword, "my", "latest", "the", "a", "an", "for",
            "called", "named", "is", "where", "are", "me", "can", "you",
            "find", "search", "look", "locate",
        }
        words = text.split()
        filtered = [w for w in words if w.lower() not in filler_words]
        query = " ".join(filtered).strip()

        generic_nouns = {"file", "files", "document", "documents", "folder", "folders"}
        stripped_words = [w for w in query.split() if w.lower() not in generic_nouns]
        if not stripped_words:
            return ""
        return query

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
