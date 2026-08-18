from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability, deterministic_report_flags
from infrastructure.services.network_info import NetworkInfoService


class NetworkInfoSkill(BaseSkill):
    """Thin presentation skill wrapper for IP address and network interface details."""

    name = "NETWORK_INFO"
    description = "Retrieves local IP address, active network interfaces, and netmask details."
    permissions = ["READ_NETWORK"]
    capability = Capability(
        name="network_info",
        description="Reads local IP address, active network interfaces, and netmask details",
        supports=["ip", "local_ip", "network", "interfaces", "netmask"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, service: NetworkInfoService | None = None) -> None:
        self.service = service or NetworkInfoService()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        net_data = self.service.get_info()
        data_dict = asdict(net_data)

        iface_lines = [f"  - {iface.name}: {iface.ip} (netmask: {iface.netmask or 'N/A'})" for iface in net_data.interfaces]
        iface_str = "\n".join(iface_lines) if iface_lines else "  - No active IPv4 interfaces found."

        query = args.get("query") or ""
        text = query.lower()
        topics: set[str] = set()
        if any(kw in text for kw in ("ip", "address")):
            topics.add("ip")
        if any(kw in text for kw in ("interface", "netmask", "network")):
            topics.add("interfaces")
        if any(kw in text for kw in ("hostname", "computer name")):
            topics.add("hostname")

        if topics:
            lines = ["Network Configuration:"]
            if "ip" in topics:
                lines.append(f"• Primary Local IP: {net_data.local_ip} (on {net_data.primary_interface})")
            if "hostname" in topics:
                lines.append(f"• Hostname: {net_data.hostname}")
            if "interfaces" in topics:
                lines.append(f"• Interfaces:\n{iface_str}")
            message = "\n".join(lines)
            use_llm, allow_interpretation = deterministic_report_flags()
            return SkillResult(
                success=True,
                data=data_dict,
                message=message,
                use_llm=use_llm,
                allow_interpretation=allow_interpretation,
            )

        message = (
            "Network Configuration:\n"
            f"• Primary Local IP: {net_data.local_ip} (on {net_data.primary_interface})\n"
            f"• Hostname: {net_data.hostname}\n"
            f"• Interfaces:\n{iface_str}"
        )

        use_llm, allow_interpretation = deterministic_report_flags()
        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=use_llm,
            allow_interpretation=allow_interpretation,
        )
