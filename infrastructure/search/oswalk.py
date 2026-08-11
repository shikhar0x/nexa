import os
import time

from config.settings import settings
from config.logger import logger
from infrastructure.os import os_adapter

from skills.path_resolver import resolve_path, SPECIAL_FOLDERS

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

PRIORITY_DIRS = [
    str(SPECIAL_FOLDERS["desktop"]),
    str(SPECIAL_FOLDERS["documents"]),
    str(SPECIAL_FOLDERS["downloads"]),
]

SKIP_DIRS = {"venv", "node_modules", "__pycache__", "snap", "flatpak"}


class OsWalkSearchBackend:
    """File search implementation using os.walk, ripgrep, and PyPDF2."""

    def search_filenames(self, query: str, search_path: str | None = None) -> list[str]:
        matches, _ = self.search_filenames_with_stats(query, search_path=search_path)
        return matches

    def search_filenames_with_stats(self, query: str, search_path: str | None = None) -> tuple[list[str], int]:
        logger.debug(f"Starting filename search for '{query}'...")
        matches = []
        files_scanned = 0
        start = time.time()
        max_results = settings.search_max_results
        query_lower = query.lower()

        search_dirs = PRIORITY_DIRS if search_path is None else [str(resolve_path(search_path))]

        for base in search_dirs:
            if not os.path.isdir(base):
                continue
            sub_matches, scanned = self._walk_search_with_stats(query_lower, base, max_results=max_results - len(matches))
            matches.extend(sub_matches)
            files_scanned += scanned
            if len(matches) >= max_results:
                return matches, files_scanned

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
                    files_scanned += 1
                    if query_lower in f.lower():
                        path = os.path.join(root, f)
                        if path not in matches:
                            matches.append(path)
                    if len(matches) >= max_results:
                        return matches, files_scanned

                if time.time() - start > settings.search_max_seconds:
                    logger.debug(f"Search timed out after {settings.search_max_seconds}s")
                    break

        return matches, files_scanned

    def _walk_search(self, query: str, search_path: str, max_results: int = 20) -> list[str]:
        matches, _ = self._walk_search_with_stats(query.lower(), search_path, max_results=max_results)
        return matches

    def _walk_search_with_stats(self, query_lower: str, search_path: str, max_results: int = 20) -> tuple[list[str], int]:
        matches = []
        scanned = 0
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in SKIP_DIRS
            ]
            for f in files:
                scanned += 1
                if query_lower in f.lower():
                    matches.append(os.path.join(root, f))
                if len(matches) >= max_results:
                    return matches, scanned
        return matches, scanned

    def search_content_fallback(self, query: str, search_path: str | None = None) -> list[str]:
        """Fall back to searching file contents (PDF, TXT, MD, DOCX, etc.) when filename matches are empty."""
        matches = []
        if not query:
            return matches

        base_path = str(resolve_path(search_path)) if search_path else os.path.expanduser("~")

        # 1. Try ripgrep content search
        try:
            rg_results = self.search_file_contents(query, search_path=base_path)
            if rg_results and not rg_results[0].startswith("ripgrep"):
                matches.extend([r for r in rg_results if r and not r.startswith("ripgrep")])
        except Exception:
            pass

        # 2. PDF content search
        try:
            pdf_results = self.search_pdf_content(query, search_path=base_path)
            clean_pdfs = [p.split(" (page ")[0] for p in pdf_results if " (page " in p or os.path.exists(p)]
            for p in clean_pdfs:
                if p not in matches and os.path.exists(p):
                    matches.append(p)
        except Exception:
            pass

        return matches[:settings.search_max_results]

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
