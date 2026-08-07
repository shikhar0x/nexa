from typing import Any
from infrastructure.monitor import get_system_data
from skills.schemas import SystemStatusData


class SystemStatusService:
    """Service providing hardware measurements (CPU, RAM, Disk, GPU, Battery, Temp)."""

    def get_status(self) -> SystemStatusData:
        data = get_system_data()
        return SystemStatusData(
            cpu_name=data["cpu_name"],
            cpu_cores_logical=data["cpu_cores_logical"],
            cpu_cores_physical=data["cpu_cores_physical"],
            cpu_freq_ghz=data.get("cpu_freq_ghz"),
            cpu_percent=data["cpu_percent"],
            gpu_name=data["gpu_name"],
            gpu_usage_percent=data.get("gpu_usage_percent"),
            gpu_vram=data.get("gpu_vram", "Shared System RAM"),
            ram_percent=data["ram_percent"],
            ram_used_gb=data["ram_used_gb"],
            ram_total_gb=data["ram_total_gb"],
            ram_free_gb=data["ram_free_gb"],
            system_drive=data.get("system_drive", "/"),
            disk_percent=data["disk_percent"],
            disk_used_gb=data["disk_used_gb"],
            disk_total_gb=data["disk_total_gb"],
            disk_free_gb=data["disk_free_gb"],
            battery_percent=data.get("battery_percent"),
            battery_plugged=data.get("battery_plugged"),
            temperature_c=data.get("temperature_c"),
            temperature_sensor=data.get("temperature_sensor"),
        )
