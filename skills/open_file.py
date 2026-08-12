import os
import time
from pathlib import Path
from typing import Any
from skills.base import BaseSkill, SkillResult, PendingAction
from skills.path_resolver import resolve_path, resolve_filename_or_path
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class OpenFileSkill(BaseSkill):
    """Skill to open files/folders via default desktop applications with safety confirmation."""

    name = "OPEN_FILE"
    description = "Opens a file or directory using default desktop application."
    permissions = ["CONFIRM_REQUIRED", "EXECUTE_APP"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        path = args.get("path", "").strip()

        # Resolve "this file", "it" from active_file in workspace_state
        if not path or path.lower() in ("this file", "it", "that document", "this document"):
            path = context.workspace_state.get("active_file", "")

        if not path:
            return SkillResult(
                success=False,
                message="No path specified to open, and no active file is set in workspace.",
                use_llm=False,
            )

        status, res_data = resolve_filename_or_path(path, context=context)

        if status == "NOT_FOUND":
            from skills.path_resolver import fuzzy_suggest_directory
            suggestions = fuzzy_suggest_directory(path, context=context)
            if suggestions:
                sug_str = "', '".join(suggestions)
                message = f"Could not open '{path}': Path does not exist. Did you mean '{sug_str}'?"
            else:
                message = f"Could not open '{path}': File or directory does not exist."

            return SkillResult(
                success=False,
                message=message,
                data={"error": "not_found", "attempted_path": path, "suggestions": suggestions},
                use_llm=False,
            )
        elif status == "MULTIPLE":
            choices: list[str] = res_data
            lines = [f"I found multiple files named '{path}':\n"]
            for idx, item in enumerate(choices, 1):
                lines.append(f"  {idx}. {item}")
            lines.append("\nWhich one would you like to open?")

            return SkillResult(
                success=False,
                message="\n".join(lines),
                data={"choices": choices, "path": path},
                use_llm=False,
                pending_action=PendingAction(
                    skill_name=self.name,
                    args={**args, "choices": choices},
                    missing_args=["path"],
                    prompt=f"Which file would you like to open?",
                    timestamp=time.time(),
                ),
            )

        resolved = res_data
        path = str(resolved)

        if not confirm_action(f"open '{path}' with your default application"):
            return SkillResult(
                success=False,
                message="Cancelled — file was not opened.",
                data={"status": "cancelled", "path": path},
                use_llm=False,
            )

        try:
            from skills.path_resolver import set_active_directory
            os_adapter.open_file(path)
            context.workspace_state["active_file"] = path
            target_dir = Path(path).parent if os.path.isfile(path) else Path(path)
            set_active_directory(context, target_dir)
            return SkillResult(
                success=True,
                message=f"Opened '{path}'.",
                data={"status": "opened", "path": path},
                use_llm=False,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"Failed to open: {e}",
                data={"path": path, "error": str(e)},
                use_llm=False,
            )
