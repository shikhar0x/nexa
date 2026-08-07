from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class VolumeSkill(BaseSkill):
    """
    Skill to query or adjust system volume / mute state.
    Reading volume is unconfirmed; setting volume or muting requires user confirmation.
    """

    name = "VOLUME_CONTROL"
    description = "Gets or sets system audio volume and mute state."
    permissions = ["CONFIRM_REQUIRED", "SYSTEM_CONTROL"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        action = args.get("action", "get")

        if action == "set":
            level = args.get("level", 50)
            if not confirm_action(f"set system volume to {level}%"):
                return SkillResult(
                    success=False,
                    message="Cancelled — volume was not changed.",
                    data={"status": "cancelled", "target_level": level},
                    use_llm=False,
                )

            res = os_adapter.set_volume(level)
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Failed to set volume: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            return SkillResult(
                success=True,
                message=f"System volume set to {level}%.",
                data=res,
                use_llm=False,
            )

        elif action in ("mute", "unmute"):
            mute_flag = (action == "mute")
            verb = "mute" if mute_flag else "unmute"
            if not confirm_action(f"{verb} system audio"):
                return SkillResult(
                    success=False,
                    message=f"Cancelled — system audio was not {verb}d.",
                    data={"status": "cancelled", "action": action},
                    use_llm=False,
                )

            res = os_adapter.set_mute(mute_flag)
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Failed to {verb} volume: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            return SkillResult(
                success=True,
                message=f"System audio is now {res.get('status', verb)}.",
                data=res,
                use_llm=False,
            )

        else:
            res = os_adapter.get_volume()
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Could not read volume: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            percent = res.get("percent", -1)
            muted = res.get("muted", False)
            mute_str = " (Muted)" if muted else ""
            msg = f"Current system volume is {percent}%{mute_str}." if percent >= 0 else "System volume could not be determined."
            return SkillResult(
                success=True,
                message=msg,
                data=res,
                use_llm=False,
            )
