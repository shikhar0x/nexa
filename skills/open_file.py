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
        path = args.get("path", "")
        if not path:
            return SkillResult(success=False, message="No path specified to open.")

        if not confirm_action(f"open '{path}' with your default application"):
            return SkillResult(
                success=False,
                message="Cancelled — file was not opened.",
                data={"status": "cancelled", "path": path},
            )

        try:
            os_adapter.open_file(path)
            return SkillResult(
                success=True,
                message=f"Opened '{path}'.",
                data={"status": "opened", "path": path},
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"Failed to open: {e}",
                data={"path": path, "error": str(e)},
            )
