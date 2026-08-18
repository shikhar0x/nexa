from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability, deterministic_report_flags
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

        sections: dict[str, str] = {
            "os": f"• OS Distro: {info_data.os_distro}",
            "version": f"• OS Version: {info_data.os_version}",
            "kernel": f"• Kernel Release: {info_data.kernel_release} ({info_data.architecture})",
            "hostname": f"• Hostname: {info_data.hostname}",
            "uptime": f"• Uptime: {info_data.uptime_formatted} (booted {info_data.boot_timestamp})",
        }

        query = args.get("query") or ""
        text = query.lower()
        topics: set[str] = set()
        if any(kw in text for kw in ("os", "distro", "operating system")):
            topics.add("os")
        if any(kw in text for kw in ("version",)):
            topics.add("version")
        if any(kw in text for kw in ("kernel",)):
            topics.add("kernel")
        if any(kw in text for kw in ("hostname", "computer name")):
            topics.add("hostname")
        if any(kw in text for kw in ("uptime", "boot", "how long")):
            topics.add("uptime")

        if topics:
            shown = [sections[t] for t in ("os", "version", "kernel", "hostname", "uptime") if t in topics and t in sections]
            if shown:
                message = "Operating System Information:\n" + "\n".join(shown)
                use_llm, allow_interpretation = deterministic_report_flags()
                return SkillResult(
                    success=True,
                    data=data_dict,
                    message=message,
                    use_llm=use_llm,
                    allow_interpretation=allow_interpretation,
                )

        message = "Operating System Information:\n" + "\n".join(sections.values())

        use_llm, allow_interpretation = deterministic_report_flags()
        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=use_llm,
            allow_interpretation=allow_interpretation,
        )
