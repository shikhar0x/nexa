import os
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from skills.path_resolver import resolve_path, resolve_filename_or_path
from config.logger import logger


SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist",
    "build", ".next", ".cache", ".pytest_cache", ".mypy_cache", ".tox",
    ".nox", ".ruff_cache", ".idea", ".vscode", ".svn", "target", "coverage",
    ".svelte-kit", ".parcel-cache", ".turbo", "out", ".output",
}

README_NAMES = ("README.md", "README.txt", "README.rst", "README", "readme.md")
ENTRY_HINTS = ("main.py", "app.py", "index.py", "manage.py", "setup.py", "pyproject.toml", "package.json", "index.js", "index.ts", "go.mod", "Cargo.toml")
INTERESTING_EXTS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".sh", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}


def _walk_repo(root: str, max_files: int = 200) -> list[str]:
    """Walk the repo tree, skipping heavy dirs, returning relative file paths."""
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            files.append(rel)
            if len(files) >= max_files:
                return files
    return files


class RepoIndexSkill(BaseSkill):
    """
    Developer-mode repo indexing. Walks the project tree (skipping heavy dirs),
    reads the README, finds the entry point, and summarizes what the project
    does. Deterministic structure + optional LLM summary of the README.
    """

    name = "REPO_INDEX"
    description = "Explains what a project does, its structure, and entry point."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="repo_index",
        description="Summarize a project: purpose, structure, entry point, tech stack",
        supports=["what does this project", "what does this repo", "codebase",
                  "repo structure", "project structure", "entry point", "tech stack"],
        requires_confirmation=False,
        deterministic=False,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        path = args.get("path", "").strip().strip("'\"") or os.getcwd()
        status, res_data = resolve_filename_or_path(path, context=context)
        if status == "NOT_FOUND":
            return SkillResult(success=False, message=f"Could not find path '{path}'.", use_llm=False)
        root = str(res_data if status == "EXACT" else path)
        if not os.path.isdir(root):
            return SkillResult(success=False, message=f"'{root}' is not a directory.", use_llm=False)

        files = _walk_repo(root)
        if not files:
            return SkillResult(success=True, message="This directory appears to be empty.", use_llm=False)

        top_dirs = sorted({f.split("/")[0] for f in files if "/" in f})[:15]
        exts: dict[str, int] = {}
        for f in files:
            ext = os.path.splitext(f)[1].lower() or "(no ext)"
            exts[ext] = exts.get(ext, 0) + 1
        top_exts = sorted(exts.items(), key=lambda x: -x[1])[:8]

        entry = next(
            (hint for hint in ENTRY_HINTS if any(os.path.basename(f) == hint for f in files)),
            files[0],
        )

        readme_path = None
        for rn in README_NAMES:
            cand = os.path.join(root, rn)
            if os.path.exists(cand):
                readme_path = cand
                break
        readme_text = ""
        if readme_path:
            try:
                with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                    readme_text = f.read()
            except Exception:
                readme_text = ""

        structure = (
            f"Project: {os.path.basename(root)}\n"
            f"• Files: {len(files)}\n"
            f"• Top-level dirs: {', '.join(top_dirs) if top_dirs else '(flat)'}\n"
            f"• File types: {', '.join(f'{e}: {c}' for e, c in top_exts)}\n"
            f"• Likely entry point: {entry}\n"
        )
        if readme_path:
            structure += f"• README: {readme_path}\n"
        else:
            structure += "• README: none found\n"

        if readme_text.strip():
            capped = readme_text[:4000]
            return SkillResult(
                success=True,
                data={"root": root, "files": files, "entry": entry, "readme": readme_text},
                message=structure + f"\nREADME Content (first {len(capped)} chars):\n\n{capped}",
                use_llm=True,
                allow_interpretation=True,
            )

        return SkillResult(
            success=True,
            data={"root": root, "files": files, "entry": entry, "readme": ""},
            message=structure + "\n(No README found — showing structure only.)",
            use_llm=False,
        )
