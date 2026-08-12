import os
import time
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability, PendingAction
from skills.path_resolver import resolve_path, resolve_filename_or_path
from config.logger import logger


try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

MAX_TEXT_CHARS = 15000

TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".html", ".css",
    ".c", ".cpp", ".h", ".java", ".go", ".rs", ".sh", ".yaml", ".yml",
    ".toml", ".ini", ".log", ".conf", ".sql",
}


class FileReaderSkill(BaseSkill):
    """
    Skill to extract text from local files (PDF, DOCX, text, markdown, source code)
    for LLM summarization and reasoning.
    """

    name = "FILE_READ"
    description = "Extracts text from PDF, DOCX, text, and source code files for LLM analysis."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="file_read",
        description="Reads text, PDF, and DOCX files for natural LLM reasoning",
        supports=["file_read", "pdf", "docx", "text"],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        path = args.get("path", "").strip().strip("'\"")

        # If path is empty or a pronoun/sentinel, check context.workspace_state for active_file
        if not path or path.lower() in ("active_file", "this file", "it", "that document", "this document"):
            path = context.workspace_state.get("active_file", "")

        if not path:
            return SkillResult(
                success=False,
                message="No target file specified to read, and no active file is selected in the workspace.",
                use_llm=False,  # Factual error bypasses LLM
            )

        search_path = args.get("search_path")
        search_dirs = [resolve_path(search_path)] if search_path else None
        status, res_data = resolve_filename_or_path(path, context=context, search_dirs=search_dirs)

        if status == "NOT_FOUND":
            from skills.path_resolver import fuzzy_suggest_directory
            suggestions = fuzzy_suggest_directory(path, context=context)
            if suggestions:
                sug_str = "', '".join(suggestions)
                message = f"Could not read file '{path}': Path does not exist. Did you mean '{sug_str}'?"
            else:
                message = f"Could not read file '{path}': File does not exist."

            return SkillResult(
                success=False,
                message=message,
                data={"error": "not_found", "attempted_path": path, "suggestions": suggestions},
                use_llm=False,  # Factual error bypasses LLM
            )
        elif status == "MULTIPLE":
            choices: list[str] = res_data
            lines = [f"I found multiple files named '{path}':\n"]
            for idx, item in enumerate(choices, 1):
                lines.append(f"  {idx}. {item}")
            lines.append("\nWhich one would you like to read?")

            return SkillResult(
                success=False,
                message="\n".join(lines),
                data={"choices": choices, "path": path},
                use_llm=False,
                pending_action=PendingAction(
                    skill_name=self.name,
                    args={**args, "choices": choices},
                    missing_args=["path"],
                    prompt=f"Which file would you like to read?",
                    timestamp=time.time(),
                ),
            )

        resolved = res_data
        path = str(resolved)

        if os.path.isdir(path):
            return SkillResult(
                success=False,
                message=f"'{path}' is a directory, not a file.",
                data={"path": path, "error": "is_directory"},
                use_llm=False,  # Factual error bypasses LLM
            )

        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".pdf":
                extracted_text = self._read_pdf(path)
            elif ext in (".docx", ".doc"):
                extracted_text = self._read_docx(path)
            elif ext in TEXT_EXTENSIONS or self._is_text_file(path):
                extracted_text = self._read_text(path)
            else:
                return SkillResult(
                    success=False,
                    message=f"File format '{ext}' is not supported for text reading.",
                    data={"path": path, "ext": ext},
                    use_llm=False,  # Factual error bypasses LLM
                )
        except Exception as e:
            logger.exception(f"Error reading file '{path}': {e}")
            return SkillResult(
                success=False,
                message=f"Could not extract text from '{path}': {e}",
                data={"path": path, "error": str(e)},
                use_llm=False,  # Factual error bypasses LLM
            )

        if not extracted_text.strip():
            return SkillResult(
                success=False,
                message=f"File '{path}' appears to be empty or contains no readable text.",
                data={"path": path},
                use_llm=False,  # Factual error bypasses LLM
            )

        # Update active_file and active working directory context
        from skills.path_resolver import set_active_directory
        context.workspace_state["active_file"] = path
        set_active_directory(context, os.path.dirname(path))

        # Safely truncate text for LLM prompt context
        original_length = len(extracted_text)
        if len(extracted_text) > MAX_TEXT_CHARS:
            extracted_text = (
                extracted_text[:MAX_TEXT_CHARS]
                + f"\n\n[... Truncated content. Total size: {original_length} characters ...]"
            )

        message = f"File Content of '{os.path.basename(path)}':\n\n{extracted_text}"

        return SkillResult(
            success=True,
            data={
                "path": path,
                "length": original_length,
                "content": extracted_text,
            },
            message=message,
            use_llm=True,  # Extracted text passed to LLM for reasoning/summarization!
            allow_interpretation=True,
        )

    def _read_pdf(self, path: str) -> str:
        if PdfReader is None:
            raise ImportError("PyPDF2 is not installed — run: pip install PyPDF2")

        reader = PdfReader(path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(pages_text)

    def _read_docx(self, path: str) -> str:
        if docx is None:
            raise ImportError("python-docx is not installed — run: pip install python-docx")
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)


    def _read_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _is_text_file(self, path: str) -> bool:
        """Check if a file appears to be plain text by reading the first 1KB."""
        try:
            with open(path, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" not in chunk
        except Exception:
            return False
