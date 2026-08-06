import psutil
from typing import Any
from infrastructure.os import os_adapter


def get_system_data() -> dict[str, Any]:
    """Return structured system data as a dict."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    # Query system drive root via active OS adapter
    drive = os_adapter.get_system_drive()
    disk = psutil.disk_usage(drive)

    data: dict[str, Any] = {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_free_gb": round(ram.available / (1024**3), 1),
        "ram_total_gb": round(ram.total / (1024**3), 1),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "system_drive": drive,
    }

    battery = psutil.sensors_battery()
    if battery:
        data["battery_percent"] = round(battery.percent, 1)
        data["battery_plugged"] = battery.power_plugged
    else:
        data["battery_percent"] = None
        data["battery_plugged"] = None

    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    data["temperature_c"] = entries[0].current
                    data["temperature_sensor"] = name
                    break
    except (AttributeError, OSError):
        pass

    return data


def format_system_data(data: dict[str, Any]) -> str:
    """Format system data dictionary into text lines."""
    lines = [
        f"CPU usage: {data['cpu_percent']}%",
        f"RAM: {data['ram_percent']}% used ({data['ram_free_gb']}GB free of {data['ram_total_gb']}GB)",
        f"Disk ({data.get('system_drive', '/')}): {data['disk_percent']}% used ({data['disk_free_gb']}GB free)",
    ]
    if data.get("battery_percent") is not None:
        status = "charging" if data["battery_plugged"] else "on battery"
        lines.append(f"Battery: {data['battery_percent']}% ({status})")
    if data.get("temperature_c"):
        lines.append(f"Temperature: {data['temperature_c']}°C ({data['temperature_sensor']})")

    return "Current system status:\n" + "\n".join(lines)
