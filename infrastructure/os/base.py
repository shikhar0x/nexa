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

    # ── Brightness Control ───────────────────────────────────────

    def get_brightness(self) -> dict:
        """Return current screen brightness as a dict with 'percent' key."""
        raise NotImplementedError

    def set_brightness(self, percent: int) -> dict:
        """Set screen brightness to given percentage (0-100)."""
        raise NotImplementedError

    # ── Volume Control ───────────────────────────────────────────

    def get_volume(self) -> dict:
        """Return current system volume as a dict with 'percent' and 'muted' keys."""
        raise NotImplementedError

    def set_volume(self, percent: int) -> dict:
        """Set system volume to given percentage (0-100)."""
        raise NotImplementedError

    def set_mute(self, mute: bool) -> dict:
        """Mute or unmute system audio."""
        raise NotImplementedError

    # ── Wi-Fi Control ────────────────────────────────────────────

    def get_wifi_status(self) -> dict:
        """Return current Wi-Fi connection status."""
        raise NotImplementedError

    def list_wifi_networks(self) -> list[dict]:
        """Return list of available Wi-Fi networks."""
        raise NotImplementedError

    def toggle_wifi(self, enable: bool) -> dict:
        """Enable or disable Wi-Fi radio."""
        raise NotImplementedError

    def connect_wifi(self, ssid: str, password: str = "") -> dict:
        """Connect to a Wi-Fi network by SSID."""
        raise NotImplementedError

    # ── Power Control ────────────────────────────────────────────

    def power_action(self, action: str, delay: int = 60) -> dict:
        """Execute a power action (shutdown/restart/sleep) with optional delay in seconds."""
        raise NotImplementedError
