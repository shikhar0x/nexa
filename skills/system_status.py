from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability, deterministic_report_flags
from infrastructure.services.system_status import SystemStatusService


class SystemStatusSkill(BaseSkill):
    """Thin presentation skill wrapper for hardware and load metrics."""

    name = "SYSTEM_STATUS"
    description = "Retrieves CPU, RAM, GPU, disk, battery, and temperature metrics."
    permissions = ["READ_SYSTEM"]
    capability = Capability(
        name="system_status",
        description="Reads real-time hardware status metrics (CPU, RAM, GPU, disk, battery, temp)",
        supports=["cpu", "memory", "ram", "disk", "gpu", "battery", "temperature"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, service: SystemStatusService | None = None) -> None:
        self.service = service or SystemStatusService()

    @staticmethod
    def _detect_topics(text: str) -> set[str]:
        """Determine which metric(s) the user explicitly asked about."""
        text = text.lower()
        topics: set[str] = set()
        if any(kw in text for kw in ("cpu", "processor", "cores")):
            topics.add("cpu")
        if any(kw in text for kw in ("ram", "memory")):
            topics.add("ram")
        if any(kw in text for kw in ("disk", "storage", "drive")):
            topics.add("disk")
        if any(kw in text for kw in ("gpu", "graphics", "video card")):
            topics.add("gpu")
        if any(kw in text for kw in ("battery", "charge", "plugged", "power")):
            topics.add("battery")
        if any(kw in text for kw in ("temp", "temperature", "thermal", "heat")):
            topics.add("temperature")
        return topics

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        status_data = self.service.get_status()
        data_dict = asdict(status_data)

        query = args.get("query") or ""
        topics = self._detect_topics(query) if query else set()
        if not topics and args.get("topics"):
            topics = set(args["topics"])

        freq_str = f" @ {status_data.cpu_freq_ghz} GHz" if status_data.cpu_freq_ghz else ""
        gpu_usage_str = f" - {status_data.gpu_usage_percent}% usage" if status_data.gpu_usage_percent is not None else ""

        sections: dict[str, str] = {
            "cpu": f"CPU: {status_data.cpu_name} ({status_data.cpu_cores_logical} logical cores / {status_data.cpu_cores_physical} physical){freq_str} - {status_data.cpu_percent}% usage",
            "gpu": f"GPU: {status_data.gpu_name}{gpu_usage_str} ({status_data.gpu_vram})",
            "ram": f"RAM: {status_data.ram_used_gb} GB used of {status_data.ram_total_gb} GB total ({status_data.ram_percent}% used, {status_data.ram_free_gb} GB available)",
            "disk": f"Storage ({status_data.system_drive}): {status_data.disk_used_gb} GB used of {status_data.disk_total_gb} GB total ({status_data.disk_percent}% used, {status_data.disk_free_gb} GB free)",
        }
        if status_data.battery_percent is not None:
            st = "charging" if status_data.battery_plugged else "discharging"
            sections["battery"] = f"Battery: {status_data.battery_percent}% ({st})"
        if status_data.temperature_c:
            sections["temperature"] = f"Temperature: {status_data.temperature_c}°C ({status_data.temperature_sensor or 'sensor'})"

        if topics:
            shown = [sections[t] for t in ("cpu", "gpu", "ram", "disk", "battery", "temperature") if t in topics and t in sections]
            if shown:
                message = "System Status:\n" + "\n".join(shown)
                use_llm, allow_interpretation = deterministic_report_flags()
                return SkillResult(
                    success=True,
                    data=data_dict,
                    message=message,
                    use_llm=use_llm,
                    allow_interpretation=allow_interpretation,
                )
            missing = ", ".join(sorted(topics))
            message = f"System Status:\n• {missing.capitalize()}: not available on this machine."
            use_llm, allow_interpretation = deterministic_report_flags()
            return SkillResult(
                success=True,
                data=data_dict,
                message=message,
                use_llm=use_llm,
                allow_interpretation=allow_interpretation,
            )

        message = "Real-time System Hardware & Status:\n" + "\n".join(sections.values())

        use_llm, allow_interpretation = deterministic_report_flags()
        # Explicit explanation request ("explain each term", "what does X mean")
        # overrides deterministic mode so the LLM interprets the report.
        if any(w in query.lower() for w in ("explain", "meaning", "mean ", "what does", "what is cpu", "what is ram", "what is gpu", "what is disk", "what is battery")):
            use_llm, allow_interpretation = True, True
        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=use_llm,
            allow_interpretation=allow_interpretation,
        )
