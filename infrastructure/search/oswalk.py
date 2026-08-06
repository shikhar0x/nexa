import os
import time

from config.settings import settings
from config.logger import logger
from infrastructure.os import os_adapter

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

PRIORITY_DIRS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
]

SKIP_DIRS = {"venv", "node_modules", "__pycache__", "snap", "flatpak"}


class OsWalkSearchBackend:
    """File search implementation using os.walk, ripgrep, and PyPDF2."""

    def search_filenames(self, query: str, search_path: str | None = None) -> list[str]:
        logger.debug(f"Starting filename search for '{query}'...")
        matches = []
        start = time.time()
        max_results = settings.search_max_results

        search_dirs = PRIORITY_DIRS if search_path is None else [search_path]

        for base in search_dirs:
            if not os.path.isdir(base):
                continue
            matches.extend(self._walk_search(query, base, max_results=max_results - len(matches)))
            if len(matches) >= max_results:
                return matches

        if search_path is None and len(matches) < max_results:
            home = os.path.expanduser("~")
            seen = {os.path.abspath(d) for d in PRIORITY_DIRS}
            for root, dirs, files in os.walk(home):
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                    and d not in SKIP_DIRS
                    and os.path.join(root, d) not in seen
                ]

                for f in files:
                    if query.lower() in f.lower():
                        path = os.path.join(root, f)
                        if path not in matches:
                            matches.append(path)
                    if len(matches) >= max_results:
                        return matches

                if time.time() - start > settings.search_max_seconds:
                    logger.debug(f"Search timed out after {settings.search_max_seconds}s")
                    break

        return matches

    def _walk_search(self, query: str, search_path: str, max_results: int = 20) -> list[str]:
        matches = []
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in SKIP_DIRS
            ]
            for f in files:
                if query.lower() in f.lower():
                    matches.append(os.path.join(root, f))
                if len(matches) >= max_results:
                    return matches
        return matches

    def search_file_contents(self, query: str, search_path: str = os.path.expanduser("~")) -> list[str]:
        logger.debug(f"Starting ripgrep content search for '{query}'...")
        try:
            result = os_adapter.run_command(
                ["rg", "--files-with-matches", "-i", "--max-count", "1", query, search_path],
                timeout=10,
            )
            return result.stdout.strip().split("\n") if result.stdout else []
        except FileNotFoundError:
            return ["ripgrep (rg) not installed — run: sudo apt install ripgrep"]

    def search_pdf_content(self, query: str, search_path: str | None = None) -> list[str]:
        if PdfReader is None:
            return ["PyPDF2 not installed — run: pip install PyPDF2"]

        logger.debug(f"Starting PDF search for '{query}'...")
        matches = []
        query_lower = query.lower()
        start = time.time()

        search_dirs = PRIORITY_DIRS if search_path is None else [search_path]

        for base in search_dirs:
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base):
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and d not in SKIP_DIRS
                ]
                for f in files:
                    if not f.lower().endswith(".pdf"):
                        continue
                    filepath = os.path.join(root, f)
                    try:
                        reader = PdfReader(filepath)
                        for page_num, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if text and query_lower in text.lower():
                                matches.append(f"{filepath} (page {page_num + 1})")
                                break
                    except Exception:
                        continue

                    if len(matches) >= 10:
                        return matches

                if time.time() - start > settings.search_max_seconds:
                    return matches

        return matches


def format_search_results(results: list[str], query: str) -> str:
    """Format file search results for LLM consumption."""
    if not results:
        return f"File search for '{query}': No matching files found."

    lines = [f"File search for '{query}' found {len(results)} result(s):"]
    for path in results[:10]:
        lines.append(f"  - {path}")
    if len(results) > 10:
        lines.append(f"  ... and {len(results) - 10} more")
    return "\n".join(lines)
