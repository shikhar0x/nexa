import os
import time
from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability, PendingAction
from skills.schemas import FileSearchResultData
from config.settings import settings
from config.logger import logger
from skills.path_resolver import resolve_path, validate_exists
from infrastructure.search.oswalk import OsWalkSearchBackend, format_search_results, normalize_file_query

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class FileSearchSkill(BaseSkill):
    """Skill to search files by filename, PDF contents, or ripgrep content."""

    name = "FILE_SEARCH"
    description = "Searches for files by filename or PDF content."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="file_search",
        description="Searches local workspace filenames and PDF documents",
        supports=["file_search", "find_file", "search_filenames"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, backend: OsWalkSearchBackend | None = None) -> None:
        self.backend = backend or OsWalkSearchBackend()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        raw_query = args.get("query", "")
        search_path = args.get("search_path") or args.get("root")

        if search_path in ("this_folder", "that_folder"):
            active_dir = getattr(context, "workspace_state", {}).get("active_directory") if context else None
            if active_dir:
                search_path = active_dir
            else:
                return SkillResult(
                    success=False,
                    message="Which directory should I search?",
                    use_llm=False,
                    pending_action=PendingAction(
                        skill_name=self.name,
                        args=dict(args),
                        missing_args=["search_path"],
                        prompt="Which directory should I search?",
                        timestamp=time.time(),
                    ),
                )

        if not raw_query:
            return SkillResult(success=False, message="No search query provided.", use_llm=False)

        if args.get("ask_directory") and not search_path:
            return SkillResult(
                success=False,
                message="Which directory should I search?",
                use_llm=False,
                pending_action=PendingAction(
                    skill_name=self.name,
                    args=dict(args),
                    missing_args=["search_path"],
                    prompt="Which directory should I search?",
                    timestamp=time.time(),
                ),
            )

        normalized_query = normalize_file_query(raw_query)
        search_root_str = str(resolve_path(search_path)) if search_path else None

        filename_matches, files_scanned = self.backend.search_filenames_with_stats(
            normalized_query, search_path=search_root_str
        )

        content_matches = []
        if not filename_matches:
            # Automatic content search fallback when filename matches are 0
            content_matches = self.backend.search_content_fallback(
                normalized_query, search_path=search_root_str
            )
            all_results = content_matches
        else:
            all_results = filename_matches

        # Debug logging as required
        if settings.debug:
            logger.debug(
                f"\n[FILE_SEARCH DEBUG TRACE]\n"
                f"  raw query                : '{raw_query}'\n"
                f"  normalized query         : '{normalized_query}'\n"
                f"  search root              : '{search_root_str or 'PRIORITY_DIRS/HOME'}'\n"
                f"  number of files scanned  : {files_scanned}\n"
                f"  number of filename matches: {len(filename_matches)}\n"
                f"  number of content matches : {len(content_matches)}\n"
                f"[END FILE_SEARCH TRACE]\n"
            )

        if all_results:
            first_match = resolve_path(all_results[0])
            from skills.path_resolver import set_active_directory
            context.workspace_state["active_file"] = str(first_match)
            set_active_directory(context, first_match.parent if first_match.is_file() else first_match)

        message = format_search_results(all_results, raw_query)
        schema_data = asdict(
            FileSearchResultData(
                query=normalized_query,
                results_count=len(all_results),
                results=all_results,
                search_backend="OsWalkSearchBackend",
            )
        )

        return SkillResult(
            success=True,
            data=schema_data,
            message=message,
            use_llm=True,
            allow_interpretation=True,
        )


class FileContentSearchSkill(BaseSkill):
    """Skill to search inside file contents using targeted text/PDF search or ripgrep."""

    name = "FILE_CONTENT_SEARCH"
    description = "Searches within text files or a specific targeted document."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="file_content_search",
        description="Searches inside text and PDF file contents via ripgrep",
        supports=["grep", "file_content_search", "search_inside"],
        requires_confirmation=False,
        deterministic=True,
    )


    def __init__(self, backend: OsWalkSearchBackend | None = None) -> None:
        self.backend = backend or OsWalkSearchBackend()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        query = args.get("query", "")
        target_file = args.get("target_file", "").strip()

        # Check if target_file is active_file or mentioned
        if target_file:
            target_file = str(resolve_path(target_file))
        else:
            active_file = context.workspace_state.get("active_file")
            if active_file and validate_exists(active_file):
                target_file = active_file

        # Targeted single-file content search
        if target_file and validate_exists(target_file) and not os.path.isdir(target_file):
            return self._search_inside_single_file(query, target_file, context)

        if not query:
            return SkillResult(success=False, message="No content query provided.", use_llm=False)

        # Global content search via ripgrep
        results = self.backend.search_file_contents(query)
        if results and not results[0].startswith("ripgrep"):
            context.workspace_state["active_file"] = results[0]

        message = format_search_results(results, query)

        return SkillResult(
            success=True,
            data={"query": query, "results": results},
            message=message,
            use_llm=True,
            allow_interpretation=True,
        )



    def _search_inside_single_file(self, query: str, filepath: str, context: Any) -> SkillResult:
        context.workspace_state["active_file"] = filepath
        query_lower = query.lower()
        matches = []
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".pdf":
            if PdfReader is None:
                return SkillResult(
                    success=False,
                    message="pypdf is not installed — run: pip install pypdf",
                    use_llm=False,
                )
            try:
                reader = PdfReader(filepath)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        if query_lower in line.lower():
                            matches.append(f"Page {page_num + 1}: {line.strip()}")
            except Exception as e:
                return SkillResult(
                    success=False,
                    message=f"Could not read PDF '{filepath}': {e}",
                    use_llm=False,
                )
        else:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            matches.append(f"Line {line_num}: {line.strip()}")
            except Exception as e:
                return SkillResult(
                    success=False,
                    message=f"Could not read file '{filepath}': {e}",
                    use_llm=False,
                )

        filename = os.path.basename(filepath)
        if not matches:
            return SkillResult(
                success=True,
                message=f"Search for '{query}' inside '{filename}': No matching lines found.",
                data={"query": query, "target_file": filepath, "matches": []},
                use_llm=False,
            )

        lines = [f"Found {len(matches)} match(es) for '{query}' inside '{filename}':\n"]
        lines.extend(f"  - {m}" for m in matches[:15])
        if len(matches) > 15:
            lines.append(f"  ... and {len(matches) - 15} more matches")

        return SkillResult(
            success=True,
            data={"query": query, "target_file": filepath, "matches": matches},
            message="\n".join(lines),
            use_llm=False,
        )
