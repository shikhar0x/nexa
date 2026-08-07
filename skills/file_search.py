import os
from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability
from skills.schemas import FileSearchResultData
from infrastructure.search.oswalk import OsWalkSearchBackend, format_search_results

try:
    from PyPDF2 import PdfReader
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
        query = args.get("query", "")
        if not query:
            return SkillResult(success=False, message="No search query provided.", use_llm=False)

        results = self.backend.search_filenames(query)

        # Also search PDFs if keywords match
        pdf_results = []
        if any(kw in query.lower() for kw in ("presentation", "pdf", "document", "report")):
            pdf_results = self.backend.search_pdf_content(query)

        # Clean PDF result strings (e.g. "/path/to.pdf (page 1)" -> "/path/to.pdf")
        clean_pdf_paths = [p.split(" (page ")[0] for p in pdf_results if " (page " in p]
        all_results = results + [p for p in clean_pdf_paths if p not in results]

        # Update active_file in workspace_state if at least one file match is found
        if all_results:
            context.workspace_state["active_file"] = all_results[0]

        message = format_search_results(all_results, query)
        schema_data = asdict(
            FileSearchResultData(
                query=query,
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
        if not target_file:
            active_file = context.workspace_state.get("active_file")
            if active_file and os.path.exists(active_file):
                target_file = active_file

        # Targeted single-file content search
        if target_file and os.path.exists(target_file) and not os.path.isdir(target_file):
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
                    message="PyPDF2 is not installed — run: pip install PyPDF2",
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
