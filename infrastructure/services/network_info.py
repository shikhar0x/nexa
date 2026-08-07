import socket
import psutil
from skills.schemas import NetworkInfoData, NetworkInterfaceInfo


class NetworkInfoService:
    """Service providing local IP addresses, active network interfaces, and netmask details."""

    def get_info(self) -> NetworkInfoData:
        hostname = socket.gethostname()

        # Find primary local IP address
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                pass

        interfaces = []
        primary_iface = "lo"

        try:
            addrs = psutil.net_if_addrs()
            for iface_name, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        ip_val = addr.address
                        if ip_val == local_ip:
                            primary_iface = iface_name
                        interfaces.append(
                            NetworkInterfaceInfo(
                                name=iface_name,
                                ip=ip_val,
                                netmask=addr.netmask,
                            )
                        )
        except Exception:
            pass

        return NetworkInfoData(
            hostname=hostname,
            local_ip=local_ip,
            primary_interface=primary_iface,
            interfaces=interfaces,
        )
