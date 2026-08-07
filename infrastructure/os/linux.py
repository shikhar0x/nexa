import subprocess
import re as _re
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

    # ── Brightness Control ───────────────────────────────────────

    def get_brightness(self) -> dict:
        """Read current screen brightness via brightnessctl."""
        logger.debug("LinuxOSAdapter reading brightness via brightnessctl")
        try:
            res = self.run_command(["brightnessctl", "info"], timeout=5)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "brightnessctl failed"}
            # Parse percentage from output like "Current brightness: 600 (47%)"
            match = _re.search(r"\((\d+)%\)", res.stdout)
            percent = int(match.group(1)) if match else -1
            return {"percent": percent, "raw_output": res.stdout.strip()}
        except FileNotFoundError:
            return {"error": "brightnessctl is not installed"}
        except Exception as e:
            return {"error": str(e)}

    def set_brightness(self, percent: int) -> dict:
        """Set screen brightness via brightnessctl."""
        percent = max(0, min(100, percent))
        logger.debug(f"LinuxOSAdapter setting brightness to {percent}% via brightnessctl")
        try:
            res = self.run_command(["brightnessctl", "set", f"{percent}%"], timeout=5)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "brightnessctl set failed"}
            return {"percent": percent, "status": "set"}
        except FileNotFoundError:
            return {"error": "brightnessctl is not installed"}
        except Exception as e:
            return {"error": str(e)}

    # ── Volume Control ───────────────────────────────────────────

    def get_volume(self) -> dict:
        """Read current system volume via pactl."""
        logger.debug("LinuxOSAdapter reading volume via pactl")
        try:
            res = self.run_command(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"], timeout=5
            )
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "pactl get-sink-volume failed"}
            match = _re.search(r"(\d+)%", res.stdout)
            percent = int(match.group(1)) if match else -1

            mute_res = self.run_command(
                ["pactl", "get-sink-mute", "@DEFAULT_SINK@"], timeout=5
            )
            muted = "yes" in mute_res.stdout.lower() if mute_res.returncode == 0 else False

            return {"percent": percent, "muted": muted}
        except FileNotFoundError:
            return {"error": "pactl is not installed"}
        except Exception as e:
            return {"error": str(e)}

    def set_volume(self, percent: int) -> dict:
        """Set system volume via pactl."""
        percent = max(0, min(150, percent))
        logger.debug(f"LinuxOSAdapter setting volume to {percent}% via pactl")
        try:
            res = self.run_command(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], timeout=5
            )
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "pactl set-sink-volume failed"}
            return {"percent": percent, "status": "set"}
        except FileNotFoundError:
            return {"error": "pactl is not installed"}
        except Exception as e:
            return {"error": str(e)}

    def set_mute(self, mute: bool) -> dict:
        """Mute or unmute system audio via pactl."""
        state = "1" if mute else "0"
        label = "muted" if mute else "unmuted"
        logger.debug(f"LinuxOSAdapter setting mute={mute} via pactl")
        try:
            res = self.run_command(
                ["pactl", "set-sink-mute", "@DEFAULT_SINK@", state], timeout=5
            )
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "pactl set-sink-mute failed"}
            return {"muted": mute, "status": label}
        except FileNotFoundError:
            return {"error": "pactl is not installed"}
        except Exception as e:
            return {"error": str(e)}

    # ── Wi-Fi Control ────────────────────────────────────────────

    def get_wifi_status(self) -> dict:
        """Check current Wi-Fi connection status via nmcli."""
        logger.debug("LinuxOSAdapter reading Wi-Fi status via nmcli")
        try:
            res = self.run_command(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY", "dev", "wifi"], timeout=10
            )
            if res.returncode != 0:
                return {"connected": False, "error": res.stderr.strip() or "nmcli failed"}

            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[0] == "yes":
                    return {
                        "connected": True,
                        "ssid": parts[1],
                        "signal": parts[2],
                        "security": parts[3],
                    }
            return {"connected": False, "ssid": None}
        except FileNotFoundError:
            return {"error": "nmcli is not installed"}
        except Exception as e:
            return {"error": str(e)}

    def list_wifi_networks(self) -> list[dict]:
        """List available Wi-Fi networks via nmcli."""
        logger.debug("LinuxOSAdapter listing Wi-Fi networks via nmcli")
        try:
            res = self.run_command(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], timeout=15
            )
            if res.returncode != 0:
                return []

            networks = []
            for line in res.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0]:
                    networks.append({
                        "ssid": parts[0],
                        "signal": parts[1],
                        "security": parts[2],
                    })
            return networks
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.warning(f"Failed to list Wi-Fi networks: {e}")
            return []

    def toggle_wifi(self, enable: bool) -> dict:
        """Enable or disable Wi-Fi radio via nmcli."""
        state = "on" if enable else "off"
        logger.debug(f"LinuxOSAdapter toggling Wi-Fi {state} via nmcli")
        try:
            res = self.run_command(["nmcli", "radio", "wifi", state], timeout=10)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or f"nmcli radio wifi {state} failed"}
            return {"wifi_enabled": enable, "status": state}
        except FileNotFoundError:
            return {"error": "nmcli is not installed"}
        except Exception as e:
            return {"error": str(e)}

    def connect_wifi(self, ssid: str, password: str = "") -> dict:
        """Connect to a Wi-Fi network via nmcli."""
        logger.debug(f"LinuxOSAdapter connecting to Wi-Fi SSID '{ssid}' via nmcli")
        try:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password]
            res = self.run_command(cmd, timeout=30)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or f"Failed to connect to '{ssid}'"}
            return {"ssid": ssid, "status": "connected"}
        except FileNotFoundError:
            return {"error": "nmcli is not installed"}
        except Exception as e:
            return {"error": str(e)}

    # ── Power Control ────────────────────────────────────────────

    def power_action(self, action: str, delay: int = 60) -> dict:
        """Execute a power action (shutdown/restart/sleep) with delay."""
        logger.debug(f"LinuxOSAdapter executing power action '{action}' with delay={delay}s")
        try:
            if action == "sleep":
                res = self.run_command(["systemctl", "suspend"], timeout=10)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "systemctl suspend failed"}
                return {"action": "sleep", "status": "initiated"}

            elif action == "shutdown":
                delay_minutes = max(1, delay // 60)
                res = self.run_command(
                    ["shutdown", "-h", f"+{delay_minutes}"], timeout=10
                )
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "shutdown command failed"}
                return {"action": "shutdown", "delay_minutes": delay_minutes, "status": "scheduled"}

            elif action == "restart":
                delay_minutes = max(1, delay // 60)
                res = self.run_command(
                    ["shutdown", "-r", f"+{delay_minutes}"], timeout=10
                )
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "restart command failed"}
                return {"action": "restart", "delay_minutes": delay_minutes, "status": "scheduled"}

            else:
                return {"error": f"Unknown power action: {action}"}
        except FileNotFoundError:
            return {"error": "shutdown/systemctl command not found"}
        except Exception as e:
            return {"error": str(e)}
