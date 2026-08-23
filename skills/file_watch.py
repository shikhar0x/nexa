import os
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from skills.path_resolver import resolve_filename_or_path
from infrastructure import file_watcher
from config.logger import logger


class FileWatchSkill(BaseSkill):
    """
    Developer-mode directory watching. Starts/stops background watches that
    fire desktop notifications on file changes. Fully deterministic — no LLM.
    Watch lifetime is the Nexa process (daemon threads).
    """

    name = "FILE_WATCH"
    description = "Watch a folder or repo for changes and notify on file events."
    permissions = ["READ_FILES"]
    capability = Capability(
        name="file_watch",
        description="Watch directories for file changes with desktop notifications",
        supports=["watch this", "watch folder", "watch repo", "notify me when files change",
                  "watch for changes", "stop watching"],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        action = (args.get("action") or "start").strip().lower()
        raw_path = (args.get("path") or "").strip().strip("'\"")

        if action == "stop":
            count, msg = file_watcher.stop_watch(raw_path or None)
            return SkillResult(success=count > 0, message=msg, use_llm=False)

        if action == "status":
            watched = file_watcher.list_watches()
            if not watched:
                return SkillResult(success=True, message="Not watching anything right now.", use_llm=False)
            body = "\n".join(f"  {p}" for p in watched)
            return SkillResult(
                success=True,
                message=f"Watching {len(watched)} director{'y' if len(watched) == 1 else 'ies'}:\n{body}",
                data={"watched": watched},
                use_llm=False,
            )

        # action == "start"
        path = raw_path or os.getcwd()
        status, res_data = resolve_filename_or_path(path, context=context)
        if status == "NOT_FOUND":
            return SkillResult(success=False, message=f"Could not find path '{path}'.", use_llm=False)
        root = str(res_data if status == "EXACT" else path)
        if not os.path.isdir(root):
            return SkillResult(success=False, message=f"'{root}' is not a directory.", use_llm=False)

        ok, msg = file_watcher.start_watch(root)
        result = SkillResult(success=ok, message=msg, use_llm=False)
        if ok:
            result.data = {"watched": root}
        return result
