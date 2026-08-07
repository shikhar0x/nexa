from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class PowerSkill(BaseSkill):
    """
    High-risk skill for system power management (shutdown, restart, sleep).
    ALWAYS requires user confirmation gate with explicit action and safety delay.
    """

    name = "POWER_CONTROL"
    description = "Shutdown, restart, or sleep the operating system safely after confirmation."
    permissions = ["CONFIRM_REQUIRED", "POWER_CONTROL", "HIGH_RISK"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        action = args.get("action", "shutdown").lower()
        delay = args.get("delay", 60)

        if action not in ("shutdown", "restart", "sleep"):
            return SkillResult(
                success=False,
                message=f"Unsupported power action '{action}'. Valid actions: shutdown, restart, sleep.",
                use_llm=False,
            )

        # High-risk safety rule: ALWAYS confirm before executing any power action
        if action == "sleep":
            confirm_msg = "put the system to sleep (suspend)"
        elif action == "restart":
            confirm_msg = f"restart the computer (scheduled with {delay}s safety delay)"
        else:
            confirm_msg = f"shut down the computer (scheduled with {delay}s safety delay)"

        if not confirm_action(confirm_msg):
            return SkillResult(
                success=False,
                message=f"Cancelled — system {action} operation aborted.",
                data={"status": "cancelled", "action": action},
                use_llm=False,
            )

        res = os_adapter.power_action(action, delay)
        if "error" in res:
            return SkillResult(
                success=False,
                message=f"Failed to execute {action}: {res['error']}",
                data=res,
                use_llm=False,
            )

        if action == "sleep":
            msg = "System suspend initiated."
        elif action == "restart":
            delay_min = res.get("delay_minutes", 1)
            msg = f"System restart scheduled in {delay_min} minute(s). Save your work!"
        else:
            delay_min = res.get("delay_minutes", 1)
            msg = f"System shutdown scheduled in {delay_min} minute(s). Save your work!"

        return SkillResult(
            success=True,
            message=msg,
            data=res,
            use_llm=False,
        )
