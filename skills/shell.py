import subprocess
from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class ShellExecutionSkill(BaseSkill):
    """Skill to safely execute shell commands via user confirmation gate."""

    name = "RUN_COMMAND"
    description = "Executes arbitrary shell commands after user confirmation."
    permissions = ["CONFIRM_REQUIRED", "EXECUTE_SHELL"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        command = args.get("command", "")
        if not command:
            return SkillResult(success=False, message="No command provided.")

        if not confirm_action(f"run shell command: {command}"):
            return SkillResult(
                success=False,
                message="Cancelled — command was not executed.",
                data={"status": "cancelled", "command": command},
            )

        try:
            result = os_adapter.run_command(command, shell=True, timeout=30)
            output = result.stdout or result.stderr or "(no output)"
            message = f"Command finished (exit code {result.returncode}):\n{output}"
            return SkillResult(
                success=(result.returncode == 0),
                message=message,
                data={
                    "command": command,
                    "returncode": result.returncode,
                    "output": output,
                },
            )
        except subprocess.TimeoutExpired:
            return SkillResult(
                success=False,
                message="Command timed out after 30 seconds.",
                data={"command": command, "error": "timeout"},
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"Failed to run command: {e}",
                data={"command": command, "error": str(e)},
            )
