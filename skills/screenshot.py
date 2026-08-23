import os
import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path
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


def _run_portal_helper() -> tuple[bool, str]:
    """Invoke scripts/portal_screenshot.py via the SYSTEM python (needs gi).

    The portal screenshot is asynchronous: the method call returns a Request
    token and the result arrives later as a Response signal. One-shot tools
    (gdbus/busctl) exit before that, and the portal cancels the request —
    the exact flakiness observed live. The helper blocks on a GLib loop
    until the real answer, so this is deterministic.

    Returns (ok, produced_png_path | error).
    """
    helper = Path(__file__).resolve().parents[1] / "scripts" / "portal_screenshot.py"
    if not helper.exists():
        return False, f"portal helper missing: {helper}"
    py = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else shutil.which("python3")
    if not py:
        return False, "no python interpreter available for the portal bridge"
    try:
        res = subprocess.run([py, str(helper)], capture_output=True, text=True, timeout=30)
    except Exception as e:
        return False, str(e)
    # Protocol: zero or more `# ...` diagnostic lines, then one final
    # `OK <path>` / `ERR <detail>` line. Scan all lines; the LAST protocol
    # line is authoritative.
    lines = (res.stdout or "").splitlines()
    verdicts = [ln for ln in lines if ln.startswith("OK ") or ln.startswith("ERR ")]
    if res.returncode == 0 and verdicts and verdicts[-1].startswith("OK "):
        return True, verdicts[-1][3:].strip()
    if verdicts and verdicts[-1].startswith("ERR "):
        return False, verdicts[-1][4:].strip()
    tail = (res.stdout or "").strip() or (res.stderr or "").strip()
    return False, tail or "portal screenshot helper failed"


def _xdg_portal_screenshot(out_path: str) -> tuple[bool, str]:
    """Capture via the XDG Desktop Portal using the GLib bridge, then move the
    produced PNG to out_path. Returns (success, error)."""
    ok, payload = _run_portal_helper()
    if not ok:
        return False, payload
    if not os.path.exists(payload):
        return False, f"portal reported success but the file is missing: {payload}"
    try:
        # shutil.move, not os.replace: out_path may be on another filesystem.
        shutil.move(payload, out_path)
    except Exception as e:
        return False, f"could not move portal screenshot into place: {e}"
    return True, ""


def _find_screenshot_backends() -> list[str]:
    """Return available screenshot backends in priority order."""
    backends: list[str] = []
    if sys.platform == "darwin" and shutil.which("screencapture"):
        backends.append("screencapture")  # native macOS tool — always first there
    if shutil.which("gdbus"):
        backends.append("gnome_shell_dbus")
    # The portal bridge needs a system python with gi, not gdbus.
    if shutil.which("gdbus") or os.path.exists("/usr/bin/python3") or shutil.which("python3"):
        backends.append("xdg_portal")
    for tool in ("gnome-screenshot", "import", "scrot", "grim"):
        if shutil.which(tool):
            backends.append(tool)
    return backends


def capture_screen_image(out_path: str) -> tuple[bool, str]:
    """Capture the full screen to out_path using the first backend that works.

    Wayland-safe by construction: the GNOME Shell and XDG portal D-Bus
    services are tried before any X11-era CLI tool. Shared by ScreenshotSkill
    (persistent capture, confirmed) and ScreenReadSkill (transient capture
    for OCR/vision).
    Returns (success, error).
    """
    backends = _find_screenshot_backends()
    if not backends:
        return False, "No screenshot backend found. Install one: sudo apt install gnome-screenshot   (or scrot / imagemagick / grim)"

    errors: list[str] = []
    for backend in backends:
        try:
            if backend == "gnome_shell_dbus":
                ok, err = _gnome_shell_screenshot(out_path)
                if ok and os.path.exists(out_path):
                    return True, ""
                errors.append(f"gnome-shell-dbus: {err or 'no file produced'}")
            elif backend == "xdg_portal":
                ok, err = _xdg_portal_screenshot(out_path)
                if ok and os.path.exists(out_path):
                    return True, ""
                errors.append(f"xdg-portal: {err or 'no file produced'}")
            elif backend == "gnome-screenshot":
                res = subprocess.run(
                    ["gnome-screenshot", "-f", out_path],
                    capture_output=True, text=True, timeout=12,
                )
                if res.returncode == 0 and os.path.exists(out_path):
                    return True, ""
                errors.append(f"gnome-screenshot: {res.stderr.strip() or 'failed'}")
            elif backend == "import":
                res = subprocess.run(
                    ["import", "-window", "root", out_path],
                    capture_output=True, text=True, timeout=15,
                )
                if res.returncode == 0 and os.path.exists(out_path):
                    return True, ""
                errors.append(f"import: {res.stderr.strip() or 'failed'}")
            elif backend == "scrot":
                res = subprocess.run(
                    ["scrot", out_path],
                    capture_output=True, text=True, timeout=15,
                )
                if res.returncode == 0 and os.path.exists(out_path):
                    return True, ""
                errors.append(f"scrot: {res.stderr.strip() or 'failed'}")
            elif backend == "screencapture":
                res = subprocess.run(
                    ["screencapture", "-x", out_path],
                    capture_output=True, text=True, timeout=15,
                )
                if res.returncode == 0 and os.path.exists(out_path):
                    return True, ""
                errors.append(f"screencapture: {res.stderr.strip() or 'failed'}")
            else:  # grim
                res = subprocess.run(
                    ["grim", out_path],
                    capture_output=True, text=True, timeout=15,
                )
                if res.returncode == 0 and os.path.exists(out_path):
                    return True, ""
                errors.append(f"grim: {res.stderr.strip() or 'failed'}")
        except Exception as e:
            errors.append(f"{backend}: {e}")
            continue

    return False, "Screenshot failed with all backends: " + "; ".join(errors)


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

        # macOS: prefer the native screencapture tool and report it explicitly.
        if sys.platform == "darwin" and shutil.which("screencapture"):
            res = subprocess.run(
                ["screencapture", "-x", out_path],
                capture_output=True, text=True, timeout=15,
            )
            if res.returncode == 0 and os.path.exists(out_path):
                return SkillResult(
                    success=True,
                    data={"path": out_path, "tool": "screencapture"},
                    message=f"Screenshot saved to {out_path}",
                    use_llm=False,
                )
            return SkillResult(
                success=False,
                message=f"screencapture failed: {res.stderr.strip() or 'unknown error'}",
                data={"error": res.stderr.strip() or "unknown error"},
                use_llm=False,
            )

        ok, err = capture_screen_image(out_path)
        if ok:
            return SkillResult(
                success=True,
                data={"path": out_path},
                message=f"Screenshot saved to {out_path}",
                use_llm=False,
            )
        return SkillResult(
            success=False,
            message=err,
            data={"error": err},
            use_llm=False,
        )
