from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability
from infrastructure.services.os_info import OSInfoService


class OSInfoSkill(BaseSkill):
    """Thin presentation skill wrapper for operating system, kernel release, and uptime."""

    name = "OS_INFO"
    description = "Retrieves OS version, distro, Linux kernel, hostname, and system uptime."
    permissions = ["READ_SYSTEM"]
    capability = Capability(
        name="os_info",
        description="Reads operating system release, distro name, Linux kernel, hostname, and uptime",
        supports=["os", "os_version", "kernel", "distro", "hostname", "uptime"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, service: OSInfoService | None = None) -> None:
        self.service = service or OSInfoService()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        info_data = self.service.get_info()
        data_dict = asdict(info_data)

        message = (
            "Operating System Information:\n"
            f"• OS Distro: {info_data.os_distro}\n"
            f"• OS Version: {info_data.os_version}\n"
            f"• Kernel Release: {info_data.kernel_release} ({info_data.architecture})\n"
            f"• Hostname: {info_data.hostname}\n"
            f"• Uptime: {info_data.uptime_formatted} (booted {info_data.boot_timestamp})"
        )

        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=True,
            allow_interpretation=True,
        )
