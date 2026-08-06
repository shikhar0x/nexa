import subprocess


class BaseOSAdapter:
    """Abstract interface defining operating-system dependent operations."""

    def open_file(self, path: str) -> None:
        """Open a file or directory with the system default application."""
        raise NotImplementedError

    def send_notification(self, title: str, body: str = "") -> bool:
        """Deliver a desktop notification."""
        raise NotImplementedError

    def get_system_drive(self) -> str:
        """Return the root path of the system drive ('/' on Linux, 'C:\\' on Windows)."""
        raise NotImplementedError

    def run_command(
        self,
        command: list[str] | str,
        capture_output: bool = True,
        timeout: float | None = None,
        shell: bool = False,
    ) -> subprocess.CompletedProcess:
        """Execute a system command via subprocess."""
        raise NotImplementedError
