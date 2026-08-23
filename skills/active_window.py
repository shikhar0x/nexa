import re
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from config.logger import logger
from infrastructure.os import os_adapter


# Common window-class → friendly name. Anything unmapped is prettified
# generically (reverse-DNS stripped, separators become spaces, capitalized).
_APP_ALIASES = {
    "code": "Visual Studio Code",
    "firefox": "Firefox",
    "google-chrome": "Google Chrome",
    "chrome": "Google Chrome",
    "slack": "Slack",
    "spotify": "Spotify",
    "gnome-terminal-server": "Terminal",
    "ptyxis": "Terminal",
    "kgx": "Console",
    "nautilus": "Files",
    "org.gnome.nautilus": "Files",
    "thunderbird": "Thunderbird",
    "obsidian": "Obsidian",
    "gedit": "Text Editor",
    "gnome-text-editor": "Text Editor",
    "vlc": "VLC",
    "telegram-desktop": "Telegram",
    "telegramdesktop": "Telegram",
    "discord": "Discord",
    "evolution": "Evolution",
    "libreoffice-writer": "LibreOffice Writer",
    "libreoffice-calc": "LibreOffice Calc",
}


def friendly_app_name(raw: str) -> str:
    """Map a window class ('code', 'gnome-terminal-server', 'org.gnome.Nautilus')
    to a human-readable application name."""
    if not raw:
        return ""
    key = raw.strip().lower()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key]
    base = key.split(".")[-1]
    name = base.replace("-", " ").replace("_", " ").strip()
    return name.capitalize() if name else raw.strip()


def natural_window_sentence(app: str, title: str) -> str:
    """Compose a conversational sentence from the raw app class and window title.

    App-style titles like "README.md - nexa - Visual Studio Code" are parsed so
    the answer reads like something a person would say
    ("Looks like you're reading README.md in Visual Studio Code (nexa).").
    """
    friendly = friendly_app_name(app)
    if title:
        parts = [p.strip() for p in title.split(" - ") if p.strip()]
        if friendly and len(parts) >= 2 and parts[-1].lower() in (
            friendly.lower(), app.lower(),
        ):
            body = parts[:-1]
            first, context = body[0], " — ".join(body[1:])
            if re.search(r"\.\w{1,6}$", first):
                msg = f"Looks like you're reading {first} in {friendly}"
                return msg + (f" ({context})." if context else ".")
            if len(body) == 1:
                # "nexa - Visual Studio Code": body is just the workspace/folder
                return f"You're in {friendly}, in the {first} workspace."
            msg = f"You're in {friendly} — {first}"
            return msg + (f" ({context})." if context else ".")
        if friendly and friendly.lower() not in title.lower() and app.lower() not in title.lower():
            return f"You're in {friendly} — \"{title}\"."
    friendly = friendly or app
    if title:
        return f"You're looking at \"{title}\"."
    if friendly:
        return f"The focused app is {friendly}, but I couldn't read its window title."
    return "A window is focused, but I couldn't read its title."


# Window classes whose titles follow the "<file> - <project> - <App>" pattern.
_EDITOR_CLASSES = {
    "code", "code-insiders", "codium", "vscodium", "sublime_text", "subl",
    "atom", "zed", "geany", "kate", "pycharm", "pycharm-ce", "idea",
    "webstorm", "clion", "goland", "nvim", "neovim", "emacs", "obsidian",
}

# Terminal classes whose titles usually embed the shell cwd ("user@host: ~/dir").
_TERMINAL_CLASSES = {
    "gnome-terminal-server", "ptyxis", "kgx", "alacritty", "kitty",
    "konsole", "xterm", "uxterm", "wezterm", "tmux", "terminator",
}


def workspace_from_title(app: str, title: str) -> str:
    """Best-effort project/workspace name parsed from a window title.

    Handles the two dominant desktop patterns, both read-only heuristics:
      * Editors:   "<file> - <workspace> - <App Name>" or
                   "<workspace> - <App Name>" (VS Code, Sublime, JetBrains, ...)
      * Terminals: "user@host: <cwd>" (GNOME Terminal, Ptyxis, ...)

    Returns "" when nothing project-like can be identified — callers should
    say so explicitly instead of guessing.
    """
    key = (app or "").strip().lower()
    if not title:
        return ""

    if key in _TERMINAL_CLASSES:
        m = re.match(r"^[^@]+@[^:]+:\s*(?P<path>.+)$", title.strip())
        if not m:
            return ""
        path = m.group("path").strip().rstrip("/")
        if not path or path == "~":
            return ""
        parts = [p for p in path.replace("~", "").split("/") if p]
        return parts[-1] if parts else ""

    if key in _EDITOR_CLASSES:
        # VS Code prefixes a dirty marker "●" to unsaved file titles; strip it.
        parts = [p.strip().lstrip("●").strip() for p in title.split(" - ")]
        parts = [p for p in parts if p]
        friendly = friendly_app_name(app)
        if len(parts) < 2 or parts[-1].lower() not in (friendly.lower(), key):
            return ""
        body = parts[:-1]
        # Doc-looking segments ("main.py") aren't projects; the remaining
        # last segment of a valid editor title is the workspace/folder.
        candidates = [p for p in body if not re.search(r"\.\w{1,6}$", p)]
        return candidates[-1] if candidates else ""

    return ""


class ActiveWindowSkill(BaseSkill):
    """Reports the currently focused window (application name + title)."""

    name = "ACTIVE_WINDOW"
    description = "Reports which application window currently has focus."
    permissions = []  # read-only desktop context; no confirmation needed
    capability = Capability(
        name="active_window",
        description="Reports the currently focused application window (app name and title)",
        supports=[
            "active window",
            "focused window",
            "current window",
            "foreground app",
        ],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        try:
            info = os_adapter.get_active_window()
        except NotImplementedError:
            return SkillResult(
                success=False,
                message="Active-window detection is not supported on this operating system yet.",
                data={"error": "not_implemented"},
                use_llm=False,
            )
        except Exception as e:
            logger.warning(f"Active-window probe raised: {e}")
            return SkillResult(
                success=False,
                message=f"Could not get the active window: {e}",
                data={"error": str(e)},
                use_llm=False,
            )

        if info.get("error"):
            hint = f" {info['hint']}" if info.get("hint") else ""
            return SkillResult(
                success=False,
                message=f"{info['error']}.{hint}".strip(),
                data=info,
                use_llm=False,
            )

        app = (info.get("app") or "").strip()
        title = (info.get("title") or "").strip()

        return SkillResult(
            success=True,
            data={**info, "app_friendly": friendly_app_name(app)},
            message=natural_window_sentence(app, title),
            use_llm=False,
        )
