import subprocess
from infrastructure.os.base import BaseOSAdapter
from config.logger import logger


class LinuxOSAdapter(BaseOSAdapter):
    """Linux-specific operating system adapter."""

    def open_file(self, path: str) -> None:
        logger.debug(f"LinuxOSAdapter launching xdg-open for path '{path}'")
        subprocess.Popen(
            ["xdg-open", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def send_notification(self, title: str, body: str = "") -> bool:
        logger.debug(f"LinuxOSAdapter triggering notify-send: '{title}' - '{body}'")
        try:
            res = self.run_command(["notify-send", title, body], timeout=5)
            return res.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"notify-send failed or not found: {e}")
            return False

    def get_system_drive(self) -> str:
        return "/"

    def run_command(
        self,
        command: list[str] | str,
        capture_output: bool = True,
        timeout: float | None = None,
        shell: bool = False,
    ) -> subprocess.CompletedProcess:
        logger.debug(f"LinuxOSAdapter running command: {command} (shell={shell})")
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=shell,
        )
