import os
import re
import time
from pathlib import Path

from config.settings import settings
from config.logger import logger
from infrastructure.os import os_adapter

from skills.path_resolver import resolve_path, validate_exists, SPECIAL_FOLDERS

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

FILLER_WORDS = {
    "find", "search", "file", "files", "related", "about", "containing",
    "named", "called", "for", "to", "my", "the", "a", "an", "latest",
    "document", "documents", "folder", "folders", "look", "locate",
    "is", "where", "are", "me", "can", "you", "in", "inside", "of",
    "show", "get", "display", "all", "any", "some", "with",
}


def normalize_file_query(query: str) -> str:
    """
    Normalizes a file search query by stripping punctuation, converting to lowercase,
    normalizing whitespace, and removing natural language filler words.
    """
    if not query:
        return ""

    text = query.lower().strip()

    # Strip punctuation except hyphens/underscores/dots inside extensions
    text = re.sub(r"[^\w\s\.-]", " ", text)
    text = re.sub(r"\.+$", "", text)
    text = re.sub(r"\.+(?=\s)", " ", text)

    words = text.split()
    filtered = [w.strip(".,;:!?") for w in words if w.strip(".,;:!?") not in FILLER_WORDS]

    if not filtered:
        filtered = [w.strip(".,;:!?") for w in words if w.strip(".,;:!?")]

    return " ".join(filtered).strip()


def _matches_query(filename: str, query: str) -> bool:
    """
    Fuzzy/token/acronym case-insensitive matching for filenames.
    Supports exact substring, word token matches, and acronym/subword sequence matches
    (e.g., 'DBMS' matching 'Resource Book DBMS.pdf', 'dbms_notes.docx', and 'Database Management Systems.pdf').
    """
    if not query:
        return False

    query_lower = query.lower().strip()
    name_lower = filename.lower()

    # 1. Exact substring match on full filename or stem
    if query_lower in name_lower:
        return True

    # 2. All query words match in filename (token matching with singular/plural prefix tolerance)
    query_words = query_lower.split()
    if len(query_words) > 1:
        def word_matches(qw: str) -> bool:
            if qw in name_lower:
                return True
            qw_stem = qw.rstrip("s")
            if len(qw_stem) >= 3 and qw_stem in name_lower:
                return True
            return False

        if all(word_matches(w) for w in query_words):
            return True

    # 3. Acronym / Subword initial matching on stem
    stem = Path(filename).stem
    raw_tokens = re.split(r'[\s_\.-]+', stem)
    initials = []
    for token in raw_tokens:
        if not token:
            continue
        initials.append(token[0].lower())
        # Collect capital letters inside camelCase tokens (e.g., DataBase -> D, B)
        caps = [c.lower() for c in token[1:] if c.isupper()]
        initials.extend(caps)

    acronym = "".join(initials)
    if query_lower in acronym:
        return True

    # 4. Fuzzy subsequence regex match across word boundaries in stem (for queries >= 2 chars)
    if len(query_lower) >= 2:
        pattern = r'(?i)' + r'.*?'.join(re.escape(c) for c in query_lower)
        if re.search(pattern, stem):
            return True

    return False


def _is_skipped(path: Path, root: Path) -> bool:
    """Check if path is inside a hidden directory or configured skipped directory."""
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts

    dir_parts = rel_parts[:-1] if path.is_file() else rel_parts
    for part in dir_parts:
        if part.startswith(".") or part in SKIP_DIRS:
            return True
    return False


class OsWalkSearchBackend:
    """File search implementation using pathlib.Path.rglob, ripgrep, and PyPDF2."""

    def search_filenames(self, query: str, search_path: str | Path | None = None) -> list[str]:
        matches, _ = self.search_filenames_with_stats(query, search_path=search_path)
        return matches

    def search_filenames_with_stats(
        self, query: str, search_path: str | Path | None = None
    ) -> tuple[list[str], int]:
        raw_query = query
        normalized_query = normalize_file_query(query) or query.lower().strip()
        matches: list[str] = []
        files_scanned = 0
        start_time = time.time()
        max_results = settings.search_max_results
        max_seconds = settings.search_max_seconds

        if search_path is not None:
            search_roots = [resolve_path(str(search_path))]
        else:
            search_roots = [resolve_path(d) for d in PRIORITY_DIRS]

        visited_roots: set[Path] = set()

        for root_path in search_roots:
            if not root_path.exists() or not root_path.is_dir():
                continue

            try:
                resolved_root = root_path.resolve()
            except Exception:
                resolved_root = root_path

            if resolved_root in visited_roots:
                continue
            visited_roots.add(resolved_root)

            try:
                for p in root_path.rglob("*"):
                    if time.time() - start_time > max_seconds:
                        logger.debug(f"Search timed out after {max_seconds}s")
                        break

                    if _is_skipped(p, root_path):
                        continue

                    if p.is_file():
                        files_scanned += 1
                        if _matches_query(p.name, normalized_query) or _matches_query(p.name, raw_query):
                            match_str = str(p)
                            if match_str not in matches:
                                matches.append(match_str)
                                if len(matches) >= max_results:
                                    break
            except Exception as e:
                logger.warning(f"Error scanning directory {root_path}: {e}")

            if len(matches) >= max_results or (time.time() - start_time > max_seconds):
                break

        # Fallback to Home directory if search_path is None and matches < max_results
        if search_path is None and len(matches) < max_results and (time.time() - start_time <= max_seconds):
            home_root = resolve_path("home")
            if home_root.exists() and home_root.is_dir():
                try:
                    resolved_home = home_root.resolve()
                except Exception:
                    resolved_home = home_root

                if resolved_home not in visited_roots:
                    try:
                        for p in home_root.rglob("*"):
                            if time.time() - start_time > max_seconds:
                                logger.debug(f"Search timed out after {max_seconds}s")
                                break

                            if _is_skipped(p, home_root):
                                continue

                            try:
                                resolved_p = p.resolve()
                                if any(resolved_p == vr or vr in resolved_p.parents for vr in visited_roots):
                                    continue
                            except Exception:
                                pass

                            if p.is_file():
                                files_scanned += 1
                                if _matches_query(p.name, normalized_query) or _matches_query(p.name, raw_query):
                                    match_str = str(p)
                                    if match_str not in matches:
                                        matches.append(match_str)
                                        if len(matches) >= max_results:
                                            break
                    except Exception as e:
                        logger.warning(f"Error scanning home directory: {e}")

        if settings.debug:
            roots_str = ", ".join(str(r) for r in search_roots)
            logger.debug(
                f"\n[FILE_SEARCH DEBUG TRACE]\n"
                f"  search root(s)           : '{roots_str}'\n"
                f"  raw query                : '{raw_query}'\n"
                f"  normalized query         : '{normalized_query}'\n"
                f"  number of files scanned  : {files_scanned}\n"
                f"  number of matches found  : {len(matches)}\n"
                f"[END FILE_SEARCH TRACE]\n"
            )

        return matches, files_scanned

    def _walk_search(self, query: str, search_path: str, max_results: int = 20) -> list[str]:
        matches, _ = self._walk_search_with_stats(query, search_path, max_results=max_results)
        return matches

    def _walk_search_with_stats(
        self, query: str, search_path: str, max_results: int = 20
    ) -> tuple[list[str], int]:
        # Backwards compatible internal helper delegating to search_filenames_with_stats
        matches, scanned = self.search_filenames_with_stats(query, search_path=search_path)
        return matches[:max_results], scanned

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

        search_dirs = [resolve_path(d) for d in PRIORITY_DIRS] if search_path is None else [resolve_path(search_path)]

        for root_path in search_dirs:
            if not root_path.exists() or not root_path.is_dir():
                continue
            try:
                for p in root_path.rglob("*.pdf"):
                    if time.time() - start > settings.search_max_seconds:
                        return matches
                    if _is_skipped(p, root_path):
                        continue
                    filepath = str(p)
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
            except Exception:
                continue

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

