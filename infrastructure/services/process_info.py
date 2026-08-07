import time
import psutil
from skills.schemas import ProcessInfoData, ProcessItem


class ProcessInfoService:
    """Service providing running process metrics and top CPU/RAM consuming processes via psutil CPU sampling."""

    def get_info(self, top_n: int = 5) -> ProcessInfoData:
        proc_objects = []

        # Pass 1: Initialize CPU percent baseline across running processes
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info', 'status']):
            try:
                p.cpu_percent(interval=None)
                proc_objects.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        time.sleep(0.1)

        # Pass 2: Measure actual CPU usage over sample interval and collect metrics
        processes = []
        for p in proc_objects:
            try:
                info = p.info
                cpu_val = p.cpu_percent(interval=None)
                ram_bytes = info['memory_info'].rss if info.get('memory_info') else 0
                ram_mb = round(ram_bytes / (1024 * 1024), 1)
                processes.append(
                    ProcessItem(
                        pid=info['pid'],
                        name=info['name'] or "unknown",
                        cpu_percent=round(cpu_val, 1),
                        ram_percent=round(info['memory_percent'] or 0.0, 1),
                        ram_mb=ram_mb,
                        status=info['status'] or "running",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        total_count = len(processes)
        top_cpu = sorted(processes, key=lambda x: (x.cpu_percent, x.ram_mb), reverse=True)[:top_n]
        top_ram = sorted(processes, key=lambda x: (x.ram_mb, x.cpu_percent), reverse=True)[:top_n]

        return ProcessInfoData(
            total_processes=total_count,
            top_cpu_processes=top_cpu,
            top_ram_processes=top_ram,
        )
