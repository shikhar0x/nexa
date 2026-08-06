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

        # 1. System status
        for kw in SYSTEM_KEYWORDS:
            if kw in text:
                result = IntentResult(intent_name="SYSTEM_STATUS")
                logger.debug(f"Classified '{user_input}' -> {result}")
                return result

        # 2. File content search
        for kw in FILE_CONTENT_KEYWORDS:
            if kw in text:
                query = text
                for k in FILE_CONTENT_KEYWORDS:
                    query = query.replace(k, "")
                result = IntentResult(
                    intent_name="FILE_CONTENT_SEARCH",
                    args={"query": query.strip()},
                )
                logger.debug(f"Classified '{user_input}' -> {result}")
                return result

        # 3. Reminder
        for kw in REMINDER_KEYWORDS:
            if kw in text:
                delay, message = self._parse_reminder(text)
                result = IntentResult(
                    intent_name="SET_REMINDER",
                    args={"delay_seconds": delay, "message": message},
                )
                logger.debug(f"Classified '{user_input}' -> {result}")
                return result

        # 4. Open file
        for kw in OPEN_KEYWORDS:
            if text.startswith(kw + " "):
                path = text[len(kw):].strip()
                if "/" in path or "." in path or any(n in text for n in FILE_NOUNS):
                    result = IntentResult(
                        intent_name="OPEN_FILE",
                        args={"path": user_input[len(kw):].strip()},
                    )
                    logger.debug(f"Classified '{user_input}' -> {result}")
                    return result

        # 5. Run command
        for kw in RUN_KEYWORDS:
            if text.startswith(kw + " "):
                cmd = user_input[len(kw):].strip()
                if cmd.lower().startswith("command "):
                    cmd = cmd[len("command "):]
                result = IntentResult(
                    intent_name="RUN_COMMAND",
                    args={"command": cmd},
                )
                logger.debug(f"Classified '{user_input}' -> {result}")
                return result

        # 6. File search
        for kw in FILE_SEARCH_KEYWORDS:
            if kw in text:
                query = self._extract_file_query(text, kw)
                if query:
                    result = IntentResult(
                        intent_name="FILE_SEARCH",
                        args={"query": query},
                    )
                    logger.debug(f"Classified '{user_input}' -> {result}")
                    return result

        if any(noun in text for noun in FILE_NOUNS):
            for kw in ("find", "where", "locate", "search", "look"):
                if kw in text:
                    query = self._extract_file_query(text, kw)
                    if query:
                        result = IntentResult(
                            intent_name="FILE_SEARCH",
                            args={"query": query},
                        )
                        logger.debug(f"Classified '{user_input}' -> {result}")
                        return result

        # Fallback intent
        result = IntentResult(intent_name="GENERAL")
        logger.debug(f"Classified '{user_input}' -> {result}")
        return result

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
