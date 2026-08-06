from typing import Any
from skills.base import BaseSkill, SkillResult
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

        if not confirm_action(f"open '{path}' with your default application"):
            return SkillResult(
                success=False,
                message="Cancelled — file was not opened.",
                data={"status": "cancelled", "path": path},
                use_llm=False,
            )

        try:
            os_adapter.open_file(path)
            context.workspace_state["active_file"] = path
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
