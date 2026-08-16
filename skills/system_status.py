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

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        status_data = self.service.get_status()
        data_dict = asdict(status_data)

        freq_str = f" @ {status_data.cpu_freq_ghz} GHz" if status_data.cpu_freq_ghz else ""
        gpu_usage_str = f" - {status_data.gpu_usage_percent}% usage" if status_data.gpu_usage_percent is not None else ""
        lines = [
            f"CPU: {status_data.cpu_name} ({status_data.cpu_cores_logical} logical cores / {status_data.cpu_cores_physical} physical){freq_str} - {status_data.cpu_percent}% usage",
            f"GPU: {status_data.gpu_name}{gpu_usage_str} ({status_data.gpu_vram})",
            f"RAM: {status_data.ram_used_gb} GB used of {status_data.ram_total_gb} GB total ({status_data.ram_percent}% used, {status_data.ram_free_gb} GB available)",
            f"Storage ({status_data.system_drive}): {status_data.disk_used_gb} GB used of {status_data.disk_total_gb} GB total ({status_data.disk_percent}% used, {status_data.disk_free_gb} GB free)",
        ]
        if status_data.battery_percent is not None:
            st = "charging" if status_data.battery_plugged else "discharging"
            lines.append(f"Battery: {status_data.battery_percent}% ({st})")
        if status_data.temperature_c:
            lines.append(f"Temperature: {status_data.temperature_c}°C ({status_data.temperature_sensor or 'sensor'})")

        message = "Real-time System Hardware & Status:\n" + "\n".join(lines)

        use_llm, allow_interpretation = deterministic_report_flags()
        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=use_llm,
            allow_interpretation=allow_interpretation,
        )
