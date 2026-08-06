import sys
from infrastructure.os.base import BaseOSAdapter
from infrastructure.os.linux import LinuxOSAdapter
from config.logger import logger


def get_os_adapter() -> BaseOSAdapter:
    """Factory function returning the OS adapter for the active operating system."""
    if sys.platform.startswith("linux"):
        logger.debug("Selected LinuxOSAdapter")
        return LinuxOSAdapter()
    elif sys.platform == "win32":
        raise NotImplementedError("Windows OS adapter is not implemented yet.")
    elif sys.platform == "darwin":
        raise NotImplementedError("macOS OS adapter is not implemented yet.")
    else:
        raise NotImplementedError(f"Unsupported operating system platform: {sys.platform}")
