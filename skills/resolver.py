from typing import Optional
from skills.base import BaseSkill
from skills.registry import SkillRegistry


class CapabilityResolver:
    """
    Capability-driven resolver that matches user intents and queries
    to one or more capability skills for execution and fan-out aggregation.
    """

    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or SkillRegistry()

    def resolve(self, intent: str, user_input: str = "") -> list[BaseSkill]:
        """
        Resolve an intent and user input query to a list of matching skills.
        Supports generic multi-skill fan-out based on capability declarations.
        """
        matched_skills: list[BaseSkill] = []
        user_input_lower = user_input.lower()

        # Check direct registry match first
        direct_skill = self.registry.get(intent)
        if direct_skill:
            matched_skills.append(direct_skill)

        # Handle SYSTEM_INFO intent fan-out dynamically based on capability tags
        if intent == "SYSTEM_INFO":
            # If user asks for comprehensive system report / specs, aggregate providers
            full_report_keywords = (
                "complete", "full", "all", "report", "specs", "specifications",
                "system info", "system details", "everything", "overview"
            )
            is_full = any(kw in user_input_lower for kw in full_report_keywords)

            # Find skills supporting hardware, OS, and network
            system_status_skill = self.registry.get("SYSTEM_STATUS")
            os_info_skill = self.registry.get("OS_INFO")
            network_info_skill = self.registry.get("NETWORK_INFO")

            if is_full:
                matched = [s for s in (system_status_skill, os_info_skill, network_info_skill) if s is not None]
                return matched if matched else matched_skills
            else:
                # Target specific capability based on query tags
                if any(kw in user_input_lower for kw in ("os", "operating system", "kernel", "distro", "hostname", "uptime", "boot", "running", "how long", "linux version")):
                    if os_info_skill:
                        return [os_info_skill]
                if any(kw in user_input_lower for kw in ("ip", "network", "interface", "mac", "netmask")):
                    if network_info_skill:
                        return [network_info_skill]
                if system_status_skill:
                    return [system_status_skill]

        # Check capability supports tags across all registered skills
        if not matched_skills:
            for skill_name in self.registry.list_skills():
                skill = self.registry.get(skill_name)
                if skill and hasattr(skill, "capability"):
                    if any(tag in user_input_lower for tag in skill.capability.supports):
                        matched_skills.append(skill)

        return matched_skills
