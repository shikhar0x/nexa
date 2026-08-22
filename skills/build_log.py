import os
import subprocess
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from skills.path_resolver import resolve_path, resolve_filename_or_path
from config.logger import logger


MAX_LOG_CHARS = 6000  # Cap on log text fed to the LLM (3B context is small)


def _read_log_file(path: str) -> tuple[bool, str]:
    """Read a text log/error file. Returns (ok, content_or_error)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return True, content
    except Exception as e:
        return False, str(e)


def _run_command_capture(cmd: str) -> tuple[int, str]:
    """Run a command and capture stdout+stderr. Returns (returncode, output)."""
    try:
        res = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return res.returncode, (res.stderr or res.stdout or "(no output)")
    except Exception as e:
        return 1, str(e)


class BuildLogSkill(BaseSkill):
    """
    Developer-mode build-log analysis. Reads a log/error file (or captures a
    command's output) and explains the error in plain language via the LLM,
    grounded strictly in the actual error text (never invented).
    """

    name = "BUILD_LOG"
    description = "Reads and explains build/test errors and log files."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="build_log",
        description="Explain build errors, test failures, and log file contents",
        supports=["error", "log", "build", "test", "traceback", "compile", "failed"],
        requires_confirmation=False,
        deterministic=False,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        path = args.get("path", "").strip().strip("'\"")
        command = args.get("command", "").strip()

        if path:
            status, res_data = resolve_filename_or_path(path, context=context)
            if status == "NOT_FOUND":
                return SkillResult(
                    success=False,
                    message=f"Could not find log file '{path}'.",
                    use_llm=False,
                )
            resolved = str(res_data)
            ok, content = _read_log_file(resolved)
            if not ok:
                return SkillResult(
                    success=False,
                    message=f"Could not read log file '{resolved}': {content}",
                    use_llm=False,
                )
            source_desc = resolved
        elif command:
            rc, content = _run_command_capture(command)
            source_desc = f"command '{command}' (exit {rc})"
        else:
            return SkillResult(
                success=False,
                message="No log file or command provided. Usage: explain error in <file>  or  run <cmd> and explain the error",
                use_llm=False,
            )

        if not content.strip():
            return SkillResult(
                success=True,
                message=f"No output/error found in {source_desc}.",
                data={"source": source_desc, "content": ""},
                use_llm=False,
            )

        original_len = len(content)
        truncated = content
        if len(truncated) > MAX_LOG_CHARS:
            truncated = (
                truncated[:MAX_LOG_CHARS]
                + f"\n\n[... Truncated. Total: {original_len} chars ...]"
            )

        return SkillResult(
            success=True,
            data={"source": source_desc, "content": content, "truncated": truncated},
            message=f"Error/Log Output from {source_desc}:\n\n{truncated}",
            use_llm=True,
            allow_interpretation=True,
        )
