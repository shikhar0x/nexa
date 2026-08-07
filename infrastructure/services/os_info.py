import platform
import socket
import time
from datetime import datetime, timedelta
import psutil
from skills.schemas import OSInfoData


class OSInfoService:
    """Service providing operating system, Linux distro, kernel release, hostname, and uptime."""

    def get_info(self) -> OSInfoData:
        uname = platform.uname()
        distro_name = "Linux"
        version_str = uname.version

        # Read /etc/os-release on Linux if available
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro_name = line.split("=", 1)[1].strip().strip('"\'')
                        break
        except Exception:
            distro_name = f"{uname.system} {uname.release}"

        boot_time_ts = psutil.boot_time()
        uptime_seconds = round(time.time() - boot_time_ts, 1)
        uptime_dt = timedelta(seconds=int(uptime_seconds))
        boot_formatted = datetime.fromtimestamp(boot_time_ts).isoformat()

        days = uptime_dt.days
        hours, remainder = divmod(uptime_dt.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m {seconds}s"

        return OSInfoData(
            os_name=uname.system,
            os_distro=distro_name,
            os_version=uname.version,
            kernel_release=uname.release,
            architecture=uname.machine,
            hostname=socket.gethostname(),
            boot_timestamp=boot_formatted,
            uptime_seconds=uptime_seconds,
            uptime_formatted=uptime_str,
        )
