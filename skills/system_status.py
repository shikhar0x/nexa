from typing import Any
from skills.base import BaseSkill, SkillResult
from infrastructure.monitor import get_system_data, format_system_data


class SystemStatusSkill(BaseSkill):
    """Skill to fetch current system health (CPU, RAM, Disk, Battery, Temp)."""

    name = "SYSTEM_STATUS"
    description = "Retrieves CPU, RAM, disk, battery, and temperature status."
    permissions = ["READ_SYSTEM"]

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        data = get_system_data()
        message = format_system_data(data)
        return SkillResult(
            success=True,
            data=data,
            message=message,
            use_llm=False,
        )

