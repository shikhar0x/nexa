from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SystemStatusData:
    """Typed schema for system hardware & load measurements."""
    cpu_name: str
    cpu_cores_logical: int
    cpu_cores_physical: int
    cpu_freq_ghz: Optional[float]
    cpu_percent: float
    gpu_name: str
    gpu_usage_percent: Optional[float]
    gpu_vram: str
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_free_gb: float
    system_drive: str
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_free_gb: float
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None
    temperature_c: Optional[float] = None
    temperature_sensor: Optional[str] = None


@dataclass
class OSInfoData:
    """Typed schema for operating system & kernel details."""
    os_name: str
    os_distro: str
    os_version: str
    kernel_release: str
    architecture: str
    hostname: str
    boot_timestamp: str
    uptime_seconds: float
    uptime_formatted: str


@dataclass
class NetworkInterfaceInfo:
    """Typed sub-schema for a single network interface."""
    name: str
    ip: str
    netmask: Optional[str] = None
    mac: Optional[str] = None


@dataclass
class NetworkInfoData:
    """Typed schema for local network configurations."""
    hostname: str
    local_ip: str
    primary_interface: str
    interfaces: list[NetworkInterfaceInfo] = field(default_factory=list)


@dataclass
class ProcessItem:
    """Typed sub-schema for a running process item."""
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float
    ram_mb: float
    status: str


@dataclass
class ProcessInfoData:
    """Typed schema for process metrics."""
    total_processes: int
    top_cpu_processes: list[ProcessItem] = field(default_factory=list)
    top_ram_processes: list[ProcessItem] = field(default_factory=list)


@dataclass
class DirectoryItem:
    """Typed sub-schema for a file or folder in a directory listing."""
    name: str
    path: str
    is_dir: bool
    size_bytes: int
    extension: str


@dataclass
class DirectoryListingData:
    """Typed schema for directory contents listing."""
    target_path: str
    total_items: int
    total_files: int
    total_directories: int
    files: list[DirectoryItem] = field(default_factory=list)
    directories: list[DirectoryItem] = field(default_factory=list)


@dataclass
class FileSearchResultData:
    """Typed schema for file search results."""
    query: str
    results_count: int
    results: list[str] = field(default_factory=list)
    search_backend: str = "OsWalkSearchBackend"
