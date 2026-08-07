import platform
import psutil
from typing import Any
from infrastructure.os import os_adapter


import re

def canonicalize_cpu_name(name: str) -> str:
    """Normalize raw CPU name string to a consistent canonical representation."""
    if not name:
        return "Generic CPU"
    cleaned = re.sub(r"\((?:R|TM)\)", "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def canonicalize_gpu_name(name: str) -> str:
    """Normalize raw GPU name string to a consistent canonical representation."""
    if not name:
        return "Integrated/Generic Graphics"
    name_lower = name.lower()
    if "iris plus" in name_lower or ("ice lake" in name_lower and "graphics" in name_lower) or "iris plus graphics g1" in name_lower:
        return "Intel Iris Plus Graphics G1"
    if "intel" in name_lower and ("uhd graphics" in name_lower or "hd graphics" in name_lower):
        return "Intel UHD Graphics"

    cleaned = re.sub(r"\(rev\s+[0-9a-fA-F]+\)", "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Intel Corporation\s+", "Intel ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^NVIDIA Corporation\s+", "NVIDIA ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^Advanced Micro Devices,?\s+Inc\.?\s+\[AMD/ATI\]\s+", "AMD ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _get_cpu_name() -> str:
    """Attempt to extract exact CPU model name from /proc/cpuinfo or platform."""
    raw_name = ""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                if "model name" in line.lower():
                    raw_name = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    if not raw_name:
        raw_name = platform.processor() or f"{platform.machine()} CPU"
    return canonicalize_cpu_name(raw_name)


def _get_gpu_details() -> dict[str, Any]:
    """Retrieve GPU model name, utilization percentage, and VRAM information."""
    name = "Integrated/Generic Graphics"
    usage_percent = None
    vram_str = None

    # 1. Attempt nvidia-smi for NVIDIA GPUs
    try:
        res = os_adapter.run_command(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                name = canonicalize_gpu_name(parts[0])
                try:
                    usage_percent = float(parts[1])
                except ValueError:
                    pass
                vram_str = f"{parts[2]} MB / {parts[3]} MB VRAM"
                return {"name": name, "usage_percent": usage_percent, "vram": vram_str}
    except Exception:
        pass

    # 2. Extract GPU model via lspci on Linux
    try:
        res = os_adapter.run_command(["lspci"], timeout=3)
        if res.returncode == 0:
            gpu_lines = []
            for line in res.stdout.splitlines():
                if any(k in line.lower() for k in ("vga compatible controller", "3d controller", "display controller")):
                    parts = line.split(":", 2)
                    gpu_name = parts[-1].strip() if len(parts) >= 3 else line
                    gpu_lines.append(gpu_name)
            if gpu_lines:
                name = canonicalize_gpu_name("; ".join(gpu_lines))
    except Exception:
        pass

    # 3. Check sysfs for AMD/Intel GPU usage percentage
    for sys_path in (
        "/sys/class/drm/card0/device/gpu_busy_percent",
        "/sys/class/drm/card1/device/gpu_busy_percent",
    ):
        try:
            with open(sys_path, "r", encoding="utf-8") as f:
                val = f.read().strip().rstrip("%")
                usage_percent = float(val)
                break
        except Exception:
            pass

    return {
        "name": canonicalize_gpu_name(name),
        "usage_percent": usage_percent,
        "vram": vram_str or "Shared System RAM (Integrated)",
    }


def get_system_data() -> dict[str, Any]:
    """Return structured real-time system hardware data as a dict."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_name = _get_cpu_name()
    cpu_count_logical = psutil.cpu_count(logical=True) or 1
    cpu_count_physical = psutil.cpu_count(logical=False) or cpu_count_logical

    try:
        freq = psutil.cpu_freq()
        cpu_freq_ghz = round(freq.current / 1000, 2) if freq and freq.current else None
    except Exception:
        cpu_freq_ghz = None

    gpu = _get_gpu_details()

    ram = psutil.virtual_memory()
    ram_used_gb = round(ram.used / (1024**3), 2)
    ram_total_gb = round(ram.total / (1024**3), 2)
    ram_free_gb = round(ram.available / (1024**3), 2)
    ram_percent = ram.percent

    drive = os_adapter.get_system_drive()
    disk = psutil.disk_usage(drive)
    disk_used_gb = round(disk.used / (1024**3), 2)
    disk_total_gb = round(disk.total / (1024**3), 2)
    disk_free_gb = round(disk.free / (1024**3), 2)
    disk_percent = disk.percent

    data: dict[str, Any] = {
        "cpu_name": cpu_name,
        "cpu_cores_logical": cpu_count_logical,
        "cpu_cores_physical": cpu_count_physical,
        "cpu_freq_ghz": cpu_freq_ghz,
        "cpu_percent": cpu_percent,
        "gpu_name": gpu["name"],
        "gpu_usage_percent": gpu["usage_percent"],
        "gpu_vram": gpu["vram"],
        "ram_percent": ram_percent,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "ram_free_gb": ram_free_gb,
        "system_drive": drive,
        "disk_percent": disk_percent,
        "disk_used_gb": disk_used_gb,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
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
    """Format system data dictionary into text lines with exact numbers."""
    freq_str = f" @ {data['cpu_freq_ghz']} GHz" if data.get("cpu_freq_ghz") else ""
    gpu_usage_str = f" - {data['gpu_usage_percent']}% usage" if data.get("gpu_usage_percent") is not None else ""
    lines = [
        f"CPU: {data['cpu_name']} ({data['cpu_cores_logical']} logical cores / {data['cpu_cores_physical']} physical){freq_str} - {data['cpu_percent']}% usage",
        f"GPU: {data['gpu_name']}{gpu_usage_str} ({data.get('gpu_vram', 'Shared System RAM')})",
        f"RAM: {data['ram_used_gb']} GB used of {data['ram_total_gb']} GB total ({data['ram_percent']}% used, {data['ram_free_gb']} GB available)",
        f"Storage ({data.get('system_drive', '/')}): {data['disk_used_gb']} GB used of {data['disk_total_gb']} GB total ({data['disk_percent']}% used, {data['disk_free_gb']} GB free)",
    ]
    if data.get("battery_percent") is not None:
        status = "charging" if data["battery_plugged"] else "discharging"
        lines.append(f"Battery: {data['battery_percent']}% ({status})")
    if data.get("temperature_c"):
        lines.append(f"Temperature: {data['temperature_c']}°C ({data.get('temperature_sensor', 'sensor')})")

    return "Real-time System Hardware & Status:\n" + "\n".join(lines)


