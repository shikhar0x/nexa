import re
from typing import Any, Optional
from pathlib import Path
from skills.path_resolver import resolve_path, SPECIAL_FOLDERS
from config.logger import logger


CANCELLATION_KEYWORDS = {"cancel", "never mind", "nevermind", "forget it", "stop", "abort"}


class ClarificationResolver:
    """
    Runtime clarification resolver that deterministically resolves pending skill missing arguments
    from conversational user responses without relying on LLM classification.
    """

    def is_cancellation(self, user_input: str) -> bool:
        """Check if user input is an explicit cancellation or abort request."""
        clean = user_input.lower().strip().rstrip(".")
        return clean in CANCELLATION_KEYWORDS or any(kw in clean for kw in CANCELLATION_KEYWORDS)

    def resolve(
        self,
        user_input: str,
        missing_args: list[str],
        context: Any,
    ) -> Optional[dict[str, Any]]:
        """
        Attempt to resolve missing arguments from user input.
        Returns a dict of {arg_name: resolved_value} if matched, or None.
        """
        if not missing_args or not user_input.strip():
            return None

        clean_text = user_input.strip().strip("'\"").rstrip(".")
        clean_lower = clean_text.lower()

        # Handle path/directory missing arguments
        path_args = {"path", "search_path", "root", "target_path", "directory", "folder"}
        target_path_arg = next((arg for arg in missing_args if arg in path_args), None)

        if target_path_arg:
            resolved_path = self._resolve_directory_input(clean_text, clean_lower, context)
            if resolved_path is not None:
                logger.debug(f"ClarificationResolver resolved '{user_input}' -> {target_path_arg}='{resolved_path}'")
                return {target_path_arg: str(resolved_path)}

        # Fallback for generic first missing argument if text matches a special folder or valid path
        first_arg = missing_args[0]
        if first_arg not in path_args:
            resolved_path = self._resolve_directory_input(clean_text, clean_lower, context)
            if resolved_path is not None:
                return {first_arg: str(resolved_path)}

        return None

    def _resolve_directory_input(
        self,
        clean_text: str,
        clean_lower: str,
        context: Any,
    ) -> Optional[Path]:
        """Resolve directory / folder clarification phrases to a Path object."""
        # 1. Direct match on special folders or home directory phrases
        if clean_lower in ("home directory", "home folder", "home", "my home directory", "in my home directory"):
            return Path.home()

        if clean_lower in ("current directory", "current folder", "here", "this directory", "this folder"):
            return Path.cwd()

        if clean_lower in ("parent directory", "parent folder", "up"):
            return Path.cwd().parent

        if clean_lower == "there":
            active_dir = getattr(context, "workspace_state", {}).get("active_directory")
            if active_dir:
                return Path(active_dir)
            return Path.home()

        # Check SPECIAL_FOLDERS lookup (e.g. "downloads", "desktop", "documents")
        folder_key = clean_lower.replace(" folder", "").replace(" directory", "").strip()
        if folder_key in SPECIAL_FOLDERS:
            return SPECIAL_FOLDERS[folder_key]

        # Check explicit path syntax (/path, ~/path, ./path) or resolve_path
        if (
            clean_text.startswith(("/", "~/", "./", "home/"))
            or re.match(r"^[a-zA-Z0-9_\-./]+$", clean_text)
        ):
            try:
                candidate = resolve_path(clean_text)
                if candidate.exists():
                    return candidate
            except Exception:
                pass

        return None
