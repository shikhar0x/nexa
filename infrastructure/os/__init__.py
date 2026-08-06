from infrastructure.os.base import BaseOSAdapter
from infrastructure.os.factory import get_os_adapter

os_adapter: BaseOSAdapter = get_os_adapter()

__all__ = ["BaseOSAdapter", "get_os_adapter", "os_adapter"]
