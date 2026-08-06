from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.search.oswalk import OsWalkSearchBackend, format_search_results


class FileSearchSkill(BaseSkill):
    """Skill to search files by filename, PDF contents, or ripgrep content."""

    name = "FILE_SEARCH"
    description = "Searches for files by filename or PDF content."
    permissions = ["READ_FILES"]

    def __init__(self, backend: OsWalkSearchBackend | None = None) -> None:
        self.backend = backend or OsWalkSearchBackend()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        query = args.get("query", "")
        if not query:
            return SkillResult(success=False, message="No search query provided.")

        results = self.backend.search_filenames(query)

        # Also search PDFs if keywords match
        pdf_results = []
        if any(kw in query.lower() for kw in ("presentation", "pdf", "document", "report")):
            pdf_results = self.backend.search_pdf_content(query)

        all_results = results + pdf_results
        message = format_search_results(all_results, query)

        return SkillResult(
            success=True,
            data={"query": query, "results": all_results},
            message=message,
        )


class FileContentSearchSkill(BaseSkill):
    """Skill to search inside file contents using ripgrep."""

    name = "FILE_CONTENT_SEARCH"
    description = "Searches within text files using ripgrep."
    permissions = ["READ_FILES"]

    def __init__(self, backend: OsWalkSearchBackend | None = None) -> None:
        self.backend = backend or OsWalkSearchBackend()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        query = args.get("query", "")
        if not query:
            return SkillResult(success=False, message="No content query provided.")

        results = self.backend.search_file_contents(query)
        message = format_search_results(results, query)

        return SkillResult(
            success=True,
            data={"query": query, "results": results},
            message=message,
        )
