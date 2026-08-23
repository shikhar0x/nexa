import os
import shutil
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

    def _pactl_available(self) -> bool:
        try:
            res = self.run_command(["pactl", "--version"], timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def _wpctl_available(self) -> bool:
        try:
            res = self.run_command(["wpctl", "--version"], timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def get_volume(self) -> dict:
        """Read current system volume, trying pactl then wpctl then amixer."""
        if self._pactl_available():
            logger.debug("LinuxOSAdapter reading volume via pactl")
            try:
                res = self.run_command(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "pactl get-sink-volume failed"}
                match = _re.search(r"(\d+)%", res.stdout)
                percent = int(match.group(1)) if match else -1
                mute_res = self.run_command(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], timeout=5)
                muted = "yes" in mute_res.stdout.lower() if mute_res.returncode == 0 else False
                return {"percent": percent, "muted": muted}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        if self._wpctl_available():
            logger.debug("LinuxOSAdapter reading volume via wpctl")
            try:
                res = self.run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "wpctl get-volume failed"}
                match = _re.search(r"([\d.]+)", res.stdout)
                percent = int(round(float(match.group(1)) * 100)) if match else -1
                muted = "MUTED" in res.stdout.upper()
                return {"percent": percent, "muted": muted}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        try:
            logger.debug("LinuxOSAdapter reading volume via amixer")
            res = self.run_command(["amixer", "get", "Master"], timeout=5)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "amixer get Master failed"}
            match = _re.search(r"(\d+)%", res.stdout)
            percent = int(match.group(1)) if match else -1
            muted = "[off]" in res.stdout.lower() or "muted" in res.stdout.lower()
            return {"percent": percent, "muted": muted}
        except FileNotFoundError:
            return {"error": "no audio backend available (pactl, wpctl, amixer all missing)"}
        except Exception as e:
            return {"error": str(e)}

    def set_volume(self, percent: int) -> dict:
        """Set system volume, trying pactl then wpctl then amixer."""
        percent = max(0, min(150, percent))
        if self._pactl_available():
            logger.debug(f"LinuxOSAdapter setting volume to {percent}% via pactl")
            try:
                res = self.run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "pactl set-sink-volume failed"}
                return {"percent": percent, "status": "set"}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        if self._wpctl_available():
            logger.debug(f"LinuxOSAdapter setting volume to {percent}% via wpctl")
            try:
                vol = percent / 100.0
                res = self.run_command(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol:.2f}"], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "wpctl set-volume failed"}
                return {"percent": percent, "status": "set"}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        try:
            logger.debug(f"LinuxOSAdapter setting volume to {percent}% via amixer")
            res = self.run_command(["amixer", "set", "Master", f"{percent}%"], timeout=5)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "amixer set Master failed"}
            return {"percent": percent, "status": "set"}
        except FileNotFoundError:
            return {"error": "no audio backend available (pactl, wpctl, amixer all missing)"}
        except Exception as e:
            return {"error": str(e)}

    def set_mute(self, mute: bool) -> dict:
        """Mute or unmute system audio, trying pactl then wpctl then amixer."""
        state = "1" if mute else "0"
        label = "muted" if mute else "unmuted"
        if self._pactl_available():
            logger.debug(f"LinuxOSAdapter setting mute={mute} via pactl")
            try:
                res = self.run_command(["pactl", "set-sink-mute", "@DEFAULT_SINK@", state], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "pactl set-sink-mute failed"}
                return {"muted": mute, "status": label}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        if self._wpctl_available():
            logger.debug(f"LinuxOSAdapter setting mute={mute} via wpctl")
            try:
                verb = "mute" if mute else "unmute"
                res = self.run_command(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", verb], timeout=5)
                if res.returncode != 0:
                    return {"error": res.stderr.strip() or "wpctl set-mute failed"}
                return {"muted": mute, "status": label}
            except FileNotFoundError:
                pass
            except Exception as e:
                return {"error": str(e)}

        try:
            logger.debug(f"LinuxOSAdapter setting mute={mute} via amixer")
            verb = "mute" if mute else "unmute"
            res = self.run_command(["amixer", "set", "Master", verb], timeout=5)
            if res.returncode != 0:
                return {"error": res.stderr.strip() or "amixer set Master failed"}
            return {"muted": mute, "status": label}
        except FileNotFoundError:
            return {"error": "no audio backend available (pactl, wpctl, amixer all missing)"}
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

    # ── Window / Desktop Context ─────────────────────────────────

    def get_active_window(self) -> dict:
        """Return the focused window's app name and title.

        Backend chain (first success wins):
          0. Nexa focused-window GNOME extension (works on Wayland AND X11)
          1. xdotool (X11 / XWayland)
          2. xprop -root + wmctrl -l (X11)
          3. GNOME Shell D-Bus Eval (X11, and Wayland only if unsafe-mode is on)
        GNOME Wayland deliberately exposes no active-window API to clients, so
        without the bundled extension we degrade to a clear error + hint.
        """
        # 0) Nexa focused-window GNOME Shell extension (best: Wayland-safe).
        # The extension exports on GNOME Shell's own bus name (org.gnome.Shell),
        # reachable without any extra well-known name.
        if shutil.which("gdbus"):
            try:
                res = subprocess.run(
                    ["gdbus", "call", "--session",
                     "--dest", "org.gnome.Shell",
                     "--object-path", "/org/nexa/FocusedWindow",
                     "--method", "org.nexa.FocusedWindow.Get"],
                    capture_output=True, text=True, timeout=5,
                )
                if res.returncode == 0:
                    m = _re.search(r"^\(\s*'(.+)',?\s*\)$", (res.stdout or "").strip(), _re.DOTALL)
                    if m:
                        import json as _json
                        # Undo GVariant text-format escapes for embedded quotes/backslashes.
                        raw = m.group(1).replace("\\'", "'").replace("\\\\", "\\")
                        try:
                            payload = _json.loads(raw)
                        except Exception:
                            payload = {}
                        if payload.get("app") or payload.get("title"):
                            return {
                                "app": payload.get("app", ""),
                                "title": payload.get("title", ""),
                                "source": "nexa-extension",
                            }
            except Exception as e:
                logger.debug(f"nexa extension active-window probe failed: {e}")

        # 1) xdotool
        if shutil.which("xdotool"):
            try:
                title_res = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=5,
                )
                if title_res.returncode == 0 and title_res.stdout.strip():
                    title = title_res.stdout.strip()
                    app = ""
                    pid_res = subprocess.run(
                        ["xdotool", "getactivewindow", "getwindowpid"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if pid_res.returncode == 0 and pid_res.stdout.strip().isdigit():
                        try:
                            import psutil
                            app = psutil.Process(int(pid_res.stdout.strip())).name()
                        except Exception:
                            app = ""
                    return {"app": app, "title": title, "source": "xdotool"}
            except Exception as e:
                logger.debug(f"xdotool active-window probe failed: {e}")

        # 2) xprop -root _NET_ACTIVE_WINDOW + wmctrl -l
        if shutil.which("xprop") and shutil.which("wmctrl"):
            try:
                root = subprocess.run(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                    capture_output=True, text=True, timeout=5,
                )
                m = _re.search(r"window id # (0x[0-9a-fA-F]+)", root.stdout or "")
                if m:
                    win_id = m.group(1).lower()
                    lst = subprocess.run(
                        ["wmctrl", "-l"], capture_output=True, text=True, timeout=5,
                    )
                    for line in (lst.stdout or "").splitlines():
                        # wmctrl -l line: "0x03a00007  0 hostname Window title..."
                        parts = line.split(None, 3)
                        if len(parts) == 4 and parts[0].lower() == win_id:
                            return {"app": "", "title": parts[3].strip(), "source": "wmctrl"}
            except Exception as e:
                logger.debug(f"xprop/wmctrl active-window probe failed: {e}")

        # 3) GNOME Shell D-Bus Eval
        if shutil.which("gdbus"):
            try:
                js = (
                    "const w=global.display.get_focus_window();"
                    "w?JSON.stringify({title:w.get_title()||'',app:w.get_wm_class()||''}):''"
                )
                res = subprocess.run(
                    ["gdbus", "call", "--session",
                     "--dest", "org.gnome.Shell",
                     "--object-path", "/org/gnome/Shell",
                     "--method", "org.gnome.Shell.Eval", js],
                    capture_output=True, text=True, timeout=5,
                )
                if res.returncode == 0:
                    m = _re.search(r"\(true,\s*'(\{.*\})'\s*\)", res.stdout or "", _re.DOTALL)
                    if m:
                        import json as _json
                        try:
                            payload = _json.loads(m.group(1))
                        except Exception:
                            payload = {}
                        if payload.get("title"):
                            return {
                                "app": payload.get("app", ""),
                                "title": payload["title"],
                                "source": "gnome-shell",
                            }
            except Exception as e:
                logger.debug(f"gnome-shell Eval active-window probe failed: {e}")

        session = os.environ.get("XDG_SESSION_TYPE", "unknown")
        if session == "wayland":
            hint = ("GNOME Wayland hides window focus from apps by design. Fix: run "
                    "'bash scripts/install_focused_window_extension.sh', log out/in once, "
                    "then 'gnome-extensions enable nexa-focused-window@nexa.local'.")
        elif not any(shutil.which(t) for t in ("xdotool", "wmctrl")):
            hint = "Install xdotool for active-window info: sudo apt install xdotool"
        else:
            hint = "No active-window backend could read the focused window."
        return {"error": "Could not determine the active window", "hint": hint, "session": session}
