import platform
import socket
import time
from datetime import datetime, timedelta
import psutil
from skills.schemas import OSInfoData


class OSInfoService:
    """Service providing operating system, Linux distro, kernel release, hostname, and uptime directly from Python system APIs."""

    def get_info(self) -> OSInfoData:
        uname = platform.uname()
        distro_name = f"{uname.system} {uname.release}"
        version_str = uname.version

        # Read /etc/os-release on Linux if available
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                os_rel = {}
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os_rel[k] = v.strip('"\'')
                if "PRETTY_NAME" in os_rel:
                    distro_name = os_rel["PRETTY_NAME"]
                elif "NAME" in os_rel:
                    distro_name = os_rel["NAME"]
                if "VERSION_ID" in os_rel:
                    version_str = os_rel["VERSION_ID"]
                elif "VERSION" in os_rel:
                    version_str = os_rel["VERSION"]
        except Exception:
            pass

        boot_time_ts = psutil.boot_time()
        uptime_seconds = round(time.time() - boot_time_ts, 1)
        uptime_dt = timedelta(seconds=int(uptime_seconds))
        boot_formatted = datetime.fromtimestamp(boot_time_ts).isoformat()

        days = uptime_dt.days
        hours, remainder = divmod(uptime_dt.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            uptime_str = f"{hours}h {minutes}m {seconds}s"

        return OSInfoData(
            os_name=platform.system(),
            os_distro=distro_name,
            os_version=version_str,
            kernel_release=platform.release(),
            architecture=platform.machine(),
            hostname=socket.gethostname(),
            boot_timestamp=boot_formatted,
            uptime_seconds=uptime_seconds,
            uptime_formatted=uptime_str,
        )
