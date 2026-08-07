from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.security import confirm_action
from infrastructure.os import os_adapter


class WifiSkill(BaseSkill):
    """
    Skill to manage Wi-Fi connections, status, and networks.
    Status check and network listing are unconfirmed; toggling radio or connecting to a network requires confirmation.
    """

    name = "WIFI_CONTROL"
    description = "Checks Wi-Fi status, lists networks, or toggles/connects Wi-Fi."
    permissions = ["CONFIRM_REQUIRED", "NETWORK_CONTROL"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        action = args.get("action", "status")

        if action == "list":
            networks = os_adapter.list_wifi_networks()
            if not networks:
                return SkillResult(
                    success=True,
                    message="No available Wi-Fi networks found.",
                    data={"networks": []},
                    use_llm=False,
                )
            lines = ["Available Wi-Fi Networks:\n"]
            for net in networks:
                lines.append(f"• {net['ssid']} (Signal: {net['signal']}%, Security: {net['security']})")
            return SkillResult(
                success=True,
                message="\n".join(lines),
                data={"networks": networks},
                use_llm=False,
            )

        elif action in ("on", "off"):
            enable = (action == "on")
            verb = "turn on" if enable else "turn off"
            if not confirm_action(f"{verb} Wi-Fi"):
                return SkillResult(
                    success=False,
                    message=f"Cancelled — Wi-Fi was not {verb}ed.",
                    data={"status": "cancelled", "target_state": action},
                    use_llm=False,
                )

            res = os_adapter.toggle_wifi(enable)
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Failed to {verb} Wi-Fi: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            return SkillResult(
                success=True,
                message=f"Wi-Fi has been turned {action}.",
                data=res,
                use_llm=False,
            )

        elif action == "connect":
            ssid = args.get("ssid", "")
            password = args.get("password", "")
            if not ssid:
                return SkillResult(
                    success=False,
                    message="No network SSID specified to connect.",
                    use_llm=False,
                )

            if not confirm_action(f"connect to Wi-Fi network '{ssid}'"):
                return SkillResult(
                    success=False,
                    message=f"Cancelled — did not connect to '{ssid}'.",
                    data={"status": "cancelled", "ssid": ssid},
                    use_llm=False,
                )

            res = os_adapter.connect_wifi(ssid, password)
            if "error" in res:
                return SkillResult(
                    success=False,
                    message=f"Failed to connect to '{ssid}': {res['error']}",
                    data=res,
                    use_llm=False,
                )

            return SkillResult(
                success=True,
                message=f"Connected to Wi-Fi network '{ssid}'.",
                data=res,
                use_llm=False,
            )

        else:
            # Status check
            res = os_adapter.get_wifi_status()
            if "error" in res and not res.get("connected"):
                return SkillResult(
                    success=False,
                    message=f"Wi-Fi status error: {res['error']}",
                    data=res,
                    use_llm=False,
                )

            if res.get("connected"):
                msg = f"Wi-Fi is connected to '{res['ssid']}' (Signal: {res['signal']}%, Security: {res['security']})."
            else:
                msg = "Wi-Fi is currently disconnected or disabled."

            return SkillResult(
                success=True,
                message=msg,
                data=res,
                use_llm=False,
            )
