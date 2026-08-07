from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class BrightnessSkill(BaseSkill):
    """
    Skill to query or adjust screen brightness.
    Reading brightness is unconfirmed; setting brightness requires user confirmation.
    """

    name = "BRIGHTNESS_CONTROL"
    description = "Gets or sets the screen brightness percentage."
    permissions = ["CONFIRM_REQUIRED", "SYSTEM_CONTROL"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        action = args.get("action", "get")

        if action == "set":
            level = args.get("level", 50)
            if not confirm_action(f"set screen brightness to {level}%"):
                return SkillResult(
                    success=False,
                    message="Cancelled — brightness was not changed.",
                    data={"status": "cancelled", "target_level": level},
                    use_llm=False,
                )

            res = os_adapter.set_brightness(level)
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Failed to set brightness: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            return SkillResult(
                success=True,
                message=f"Screen brightness set to {level}%.",
                data=res,
                use_llm=False,
            )

        else:
            res = os_adapter.get_brightness()
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Could not read brightness: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            percent = res.get("percent", -1)
            msg = f"Current screen brightness is {percent}%." if percent >= 0 else "Screen brightness could not be determined."
            return SkillResult(
                success=True,
                message=msg,
                data=res,
                use_llm=False,
            )
