import os
import subprocess
import shutil
from datetime import datetime
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from infrastructure.security import confirm_action


def _gnome_shell_screenshot(out_path: str) -> tuple[bool, str]:
    """Capture via the GNOME Shell screenshot D-Bus service (Wayland-native,
    synchronous, writes directly to out_path). Returns (success, error)."""
    if not shutil.which("gdbus"):
        return False, "gdbus not available"
    try:
        res = subprocess.run(
            [
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Shell.Screenshot",
                "--object-path", "/org/gnome/Shell/Screenshot",
                "--method", "org.gnome.Shell.Screenshot.Screenshot",
                "false",   # include_cursor
                "false",   # flash
                out_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if res.returncode == 0:
            return True, ""
        return False, res.stderr.strip() or "gnome-shell screenshot call failed"
    except Exception as e:
        return False, str(e)


def _xdg_portal_screenshot(out_path: str) -> tuple[bool, str]:
    """Capture via the XDG Desktop Portal (PrtSc backend)."""
    if not shutil.which("gdbus"):
        return False, "gdbus not available"
    try:
        res = subprocess.run(
            [
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.portal.Desktop",
                "--object-path", "/org/freedesktop/portal/desktop",
                "--method", "org.freedesktop.portal.Screenshot.Screenshot",
                "",                  # parent_window
                "{'interactive': <false>}",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if res.returncode != 0:
            return False, res.stderr.strip() or "portal screenshot call failed"
        return True, ""
    except Exception as e:
        return False, str(e)


def _find_screenshot_backends() -> list[str]:
    """Return available screenshot backends in priority order."""
    backends: list[str] = []
    if shutil.which("gdbus"):
        backends.append("gnome_shell_dbus")
        backends.append("xdg_portal")
    for tool in ("gnome-screenshot", "import", "scrot", "grim"):
        if shutil.which(tool):
            backends.append(tool)
    return backends


class ScreenshotSkill(BaseSkill):
    """Takes a full-screen screenshot using the system's screenshot tool."""

    name = "SCREENSHOT"
    description = "Captures the full screen to a PNG file in ~/Pictures/Screenshots."
    permissions = ["CONFIRM_REQUIRED", "SYSTEM_CONTROL"]
    capability = Capability(
        name="screenshot",
        description="Captures a full-screen screenshot to a PNG file",
        supports=["screenshot", "capture screen", "screen capture"],
        requires_confirmation=True,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        if not confirm_action("take a full-screen screenshot"):
            return SkillResult(
                success=False,
                message="Cancelled — screenshot was not taken.",
                data={"status": "cancelled"},
                use_llm=False,
            )

        shots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
        os.makedirs(shots_dir, exist_ok=True)
        filename = "screenshot_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        out_path = os.path.join(shots_dir, filename)

        backends = _find_screenshot_backends()
        if not backends:
            return SkillResult(
                success=False,
                message="No screenshot backend found. Install one: sudo apt install gnome-screenshot   (or scrot / imagemagick / grim)",
                data={"error": "no_tool"},
                use_llm=False,
            )

        last_error = ""
        for backend in backends:
            try:
                if backend == "gnome_shell_dbus":
                    ok, err = _gnome_shell_screenshot(out_path)
                    if ok and os.path.exists(out_path):
                        return SkillResult(
                            success=True,
                            data={"path": out_path, "tool": backend},
                            message=f"Screenshot saved to {out_path}",
                            use_llm=False,
                        )
                    last_error = f"gnome-shell-dbus: {err or 'no file produced'}"
                elif backend == "xdg_portal":
                    ok, err = _xdg_portal_screenshot(out_path)
                    portal_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
                    if ok and os.path.isdir(portal_dir):
                        shots = sorted(
                            (os.path.join(portal_dir, f) for f in os.listdir(portal_dir) if f.endswith(".png")),
                            key=os.path.getmtime,
                        )
                        if shots:
                            latest = shots[-1]
                            os.replace(latest, out_path)
                            return SkillResult(
                                success=True,
                                data={"path": out_path, "tool": backend},
                                message=f"Screenshot saved to {out_path}",
                                use_llm=False,
                            )
                    last_error = f"xdg-portal: {err or 'no file found'}"
                elif backend == "gnome-screenshot":
                    res = subprocess.run(
                        ["gnome-screenshot", "-f", out_path],
                        capture_output=True, text=True, timeout=12,
                    )
                    if res.returncode == 0 and os.path.exists(out_path):
                        return SkillResult(
                            success=True,
                            data={"path": out_path, "tool": backend},
                            message=f"Screenshot saved to {out_path}",
                            use_llm=False,
                        )
                    last_error = f"gnome-screenshot: {res.stderr.strip() or 'failed'}"
                elif backend == "import":
                    res = subprocess.run(
                        ["import", "-window", "root", out_path],
                        capture_output=True, text=True, timeout=15,
                    )
                    if res.returncode == 0 and os.path.exists(out_path):
                        return SkillResult(
                            success=True,
                            data={"path": out_path, "tool": backend},
                            message=f"Screenshot saved to {out_path}",
                            use_llm=False,
                        )
                    last_error = f"import: {res.stderr.strip() or 'failed'}"
                elif backend == "scrot":
                    res = subprocess.run(
                        ["scrot", out_path],
                        capture_output=True, text=True, timeout=15,
                    )
                    if res.returncode == 0 and os.path.exists(out_path):
                        return SkillResult(
                            success=True,
                            data={"path": out_path, "tool": backend},
                            message=f"Screenshot saved to {out_path}",
                            use_llm=False,
                        )
                    last_error = f"scrot: {res.stderr.strip() or 'failed'}"
                else:  # grim
                    res = subprocess.run(
                        ["grim", out_path],
                        capture_output=True, text=True, timeout=15,
                    )
                    if res.returncode == 0 and os.path.exists(out_path):
                        return SkillResult(
                            success=True,
                            data={"path": out_path, "tool": backend},
                            message=f"Screenshot saved to {out_path}",
                            use_llm=False,
                        )
                    last_error = f"grim: {res.stderr.strip() or 'failed'}"
            except Exception as e:
                last_error = f"{backend}: {e}"
                continue

        return SkillResult(
            success=False,
            message=f"Screenshot failed with all backends: {last_error}",
            data={"error": last_error},
            use_llm=False,
        )
