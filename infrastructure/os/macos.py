import subprocess
import re as _re
import ctypes
from ctypes.util import find_library
from infrastructure.os.base import BaseOSAdapter
from config.logger import logger


# Load CoreGraphics CGMainDisplayID dynamically
try:
    _app_services_path = find_library("ApplicationServices")
    if _app_services_path:
        _app_services = ctypes.cdll.LoadLibrary(_app_services_path)
        _app_services.CGMainDisplayID.restype = ctypes.c_uint32
    else:
        _app_services = None
except Exception as e:
    logger.warning(f"Failed to load ApplicationServices via ctypes: {e}")
    _app_services = None


# Load private DisplayServices framework dynamically for brightness controls
try:
    _ds_path = "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
    _ds = ctypes.CDLL(_ds_path)
    _ds.DisplayServicesGetBrightness.restype = ctypes.c_int
    _ds.DisplayServicesGetBrightness.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
    _ds.DisplayServicesSetBrightness.restype = ctypes.c_int
    _ds.DisplayServicesSetBrightness.argtypes = [ctypes.c_uint32, ctypes.c_float]
except Exception as e:
    logger.warning(f"Failed to load DisplayServices via ctypes: {e}")
    _ds = None


class MacOSAdapter(BaseOSAdapter):
    """macOS-specific operating system adapter."""

    def open_file(self, path: str) -> None:
        logger.debug(f"MacOSAdapter launching open for path '{path}'")
        subprocess.Popen(
            ["open", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def send_notification(self, title: str, body: str = "") -> bool:
        logger.debug(f"MacOSAdapter triggering osascript notification: '{title}' - '{body}'")
        try:
            # Escape double quotes for AppleScript string format
            escaped_title = title.replace('"', '\\"')
            escaped_body = body.replace('"', '\\"')
            script = f'display notification "{escaped_body}" with title "{escaped_title}"'
            res = self.run_command(["osascript", "-e", script], timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"osascript notification failed: {e}")
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
        logger.debug(f"MacOSAdapter running command: {command} (shell={shell})")
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=shell,
        )

    # ── Brightness Control ───────────────────────────────────────

    def get_brightness(self) -> dict:
        """Read screen brightness via DisplayServices."""
        if not _app_services or not _ds:
            return {"error": "DisplayServices ctypes library is not available"}
        try:
            display_id = _app_services.CGMainDisplayID()
            brightness = ctypes.c_float(0.0)
            res = _ds.DisplayServicesGetBrightness(display_id, ctypes.byref(brightness))
            if res == 0:
                percent = int(round(brightness.value * 100))
                return {"percent": percent}
            return {"error": f"DisplayServicesGetBrightness returned error code {res}"}
        except Exception as e:
            return {"error": str(e)}

    def set_brightness(self, percent: int) -> dict:
        """Set screen brightness via DisplayServices."""
        if not _app_services or not _ds:
            return {"error": "DisplayServices ctypes library is not available"}
        percent = max(0, min(100, percent))
        val = percent / 100.0
        try:
            display_id = _app_services.CGMainDisplayID()
            res = _ds.DisplayServicesSetBrightness(display_id, ctypes.c_float(val))
            if res == 0:
                return {"percent": percent, "status": "set"}
            return {"error": f"DisplayServicesSetBrightness returned error code {res}"}
        except Exception as e:
            return {"error": str(e)}

    # ── Volume Control ───────────────────────────────────────────

    def get_volume(self) -> dict:
        """Read system volume via osascript."""
        try:
            vol_res = self.run_command(["osascript", "-e", "output volume of (get volume settings)"])
            if vol_res.returncode != 0:
                return {"error": vol_res.stderr.strip() or "osascript get volume failed"}
            
            mute_res = self.run_command(["osascript", "-e", "output muted of (get volume settings)"])
            if mute_res.returncode != 0:
                return {"error": mute_res.stderr.strip() or "osascript get mute failed"}

            percent = int(vol_res.stdout.strip())
            muted = mute_res.stdout.strip() == "true"
            return {"percent": percent, "muted": muted}
        except Exception as e:
            return {"error": str(e)}

    def set_volume(self, percent: int) -> dict:
        """Set system volume via osascript."""
        percent = max(0, min(100, percent))
        try:
            res = self.run_command(["osascript", "-e", f"set volume output volume {percent}"])
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "osascript set volume failed"}
            return {"percent": percent, "status": "set"}
        except Exception as e:
            return {"error": str(e)}

    def set_mute(self, mute: bool) -> dict:
        """Mute or unmute system audio via osascript."""
        state = "true" if mute else "false"
        label = "muted" if mute else "unmuted"
        try:
            res = self.run_command(["osascript", "-e", f"set volume output muted {state}"])
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "osascript set mute failed"}
            return {"muted": mute, "status": label}
        except Exception as e:
            return {"error": str(e)}

    # ── Wi-Fi Control ────────────────────────────────────────────

    def _get_wifi_interface(self) -> str:
        """Get network Wi-Fi device interface name (e.g. en0)."""
        try:
            res = self.run_command(["networksetup", "-listallhardwareports"], timeout=5)
            lines = res.stdout.splitlines()
            for i, line in enumerate(lines):
                if "Hardware Port: Wi-Fi" in line and i + 1 < len(lines):
                    device_line = lines[i + 1]
                    match = _re.search(r"Device:\s*(\w+)", device_line)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return "en0"

    def get_wifi_status(self) -> dict:
        """Get current connected Wi-Fi SSID and signal details."""
        interface = self._get_wifi_interface()
        try:
            power_res = self.run_command(["networksetup", "-getairportpower", interface], timeout=5)
            enabled = "On" in power_res.stdout
            
            if not enabled:
                return {"connected": False, "ssid": None}

            net_res = self.run_command(["networksetup", "-getairportnetwork", interface], timeout=5)
            if "Current Wi-Fi Network" in net_res.stdout:
                ssid = net_res.stdout.split("Current Wi-Fi Network:")[-1].strip()
                signal = "N/A"
                security = "Unknown"
                try:
                    prof_res = self.run_command(["system_profiler", "SPAirPortDataType"], timeout=10)
                    lines = prof_res.stdout.splitlines()
                    in_current = False
                    for line in lines:
                        stripped = line.strip()
                        if "Current Network Information:" in line:
                            in_current = True
                            continue
                        if in_current:
                            if stripped and len(line) - len(stripped) <= 10:
                                break
                            if ":" in stripped:
                                key, val = stripped.split(":", 1)
                                key = key.strip()
                                val = val.strip()
                                if key == "Security":
                                    security = val
                                elif key == "Signal / Noise":
                                    signal = val.split("/")[0].strip()
                except Exception:
                    pass
                return {
                    "connected": True,
                    "ssid": ssid,
                    "signal": signal,
                    "security": security
                }
            
            return {"connected": False, "ssid": None}
        except Exception as e:
            return {"error": str(e)}

    def list_wifi_networks(self) -> list[dict]:
        """List nearby Wi-Fi SSIDs by parsing system_profiler."""
        try:
            res = self.run_command(["system_profiler", "SPAirPortDataType"], timeout=15)
            lines = res.stdout.splitlines()
            networks = []
            
            in_other = False
            current_ssid = None
            current_security = "Unknown"
            current_signal = None
            
            for line in lines:
                if "Other Local Wi-Fi Networks:" in line:
                    in_other = True
                    continue
                if in_other:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    
                    indent = len(line) - len(stripped)
                    if indent <= 10 and not stripped.startswith("Other Local Wi-Fi Networks"):
                        in_other = False
                        break
                    
                    if indent == 12:
                        if current_ssid:
                            networks.append({
                                "ssid": current_ssid,
                                "signal": current_signal or "N/A",
                                "security": current_security
                            })
                        current_ssid = stripped.rstrip(":")
                        current_security = "Unknown"
                        current_signal = None
                    elif indent == 14 and current_ssid:
                        if ":" in stripped:
                            key, val = stripped.split(":", 1)
                            key = key.strip()
                            val = val.strip()
                            if key == "Security":
                                current_security = val
                            elif key == "Signal / Noise":
                                current_signal = val.split("/")[0].strip()
            
            if current_ssid:
                networks.append({
                    "ssid": current_ssid,
                    "signal": current_signal or "N/A",
                    "security": current_security
                })
            return networks
        except Exception as e:
            logger.warning(f"Failed to list Wi-Fi networks: {e}")
            return []

    def toggle_wifi(self, enable: bool) -> dict:
        """Toggle Wi-Fi power."""
        interface = self._get_wifi_interface()
        state = "on" if enable else "off"
        try:
            res = self.run_command(["networksetup", "-setairportpower", interface, state], timeout=10)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or f"networksetup setairportpower {state} failed"}
            return {"wifi_enabled": enable, "status": state}
        except Exception as e:
            return {"error": str(e)}

    def connect_wifi(self, ssid: str, password: str = "") -> dict:
        """Connect to network by SSID."""
        interface = self._get_wifi_interface()
        try:
            cmd = ["networksetup", "-setairportnetwork", interface, ssid]
            if password:
                cmd.append(password)
            res = self.run_command(cmd, timeout=30)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or f"networksetup setairportnetwork failed"}
            return {"ssid": ssid, "status": "connected"}
        except Exception as e:
            return {"error": str(e)}

    # ── Power Control ────────────────────────────────────────────

    def power_action(self, action: str, delay: int = 60) -> dict:
        """Perform system power action (sleep/shutdown/restart)."""
        logger.debug(f"MacOSAdapter executing power action '{action}' with delay={delay}s")
        try:
            if action == "sleep":
                res = self.run_command(["pmset", "sleepnow"], timeout=10)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "pmset sleepnow failed"}
                return {"action": "sleep", "status": "initiated"}
            
            elif action == "shutdown":
                res = self.run_command(["osascript", "-e", 'tell application "System Events" to shut down'], timeout=10)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "osascript shut down failed"}
                return {"action": "shutdown", "status": "initiated"}
                
            elif action == "restart":
                res = self.run_command(["osascript", "-e", 'tell application "System Events" to restart'], timeout=10)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "osascript restart failed"}
                return {"action": "restart", "status": "initiated"}
            
            else:
                return {"error": f"Unknown power action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    # ── Window / Desktop Context ─────────────────────────────────

    def get_active_window(self) -> dict:
        """Return the frontmost app's name and front-window title via AppleScript."""
        try:
            app_res = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of '
                 'first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=8,
            )
            if app_res.returncode != 0 or not app_res.stdout.strip():
                return {
                    "error": app_res.stderr.strip() or "Could not determine the frontmost application",
                    "hint": "Grant accessibility/Automation permission to the terminal app in "
                            "System Settings → Privacy & Security.",
                }
            app = app_res.stdout.strip()
            title = ""
            try:
                title_res = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to tell (first application process '
                     'whose frontmost is true) to get name of front window'],
                    capture_output=True, text=True, timeout=8,
                )
                if title_res.returncode == 0:
                    title = title_res.stdout.strip()
            except Exception:
                title = ""
            return {"app": app, "title": title, "source": "applescript"}
        except Exception as e:
            return {"error": str(e)}
