"""In-session directory watching (developer mode).

Watch lifetime = the Nexa process: watcher threads are daemonized, so all
watches stop when Nexa exits (documented in the skill's start message).
Each change batch fires a desktop notification plus a log line.
"""
import os
import threading
import time

from config.logger import logger
from infrastructure.notifications import send_notification

_lock = threading.Lock()
_active: dict[str, "DirWatch"] = {}

MAX_NOTIFY_PATHS = 5

_CHANGE_LABELS = {1: "added", 2: "modified", 3: "deleted"}


class DirWatch:
    """One background watch session for a single directory."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.started_at = time.time()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name=f"nexa-watch:{path}", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        try:
            from watchfiles import watch
        except ImportError:
            logger.warning("watchfiles is not installed; directory watching unavailable")
            _deregister(self.path)
            return
        try:
            for changes in watch(
                self.path, stop_event=self._stop_event, debounce=800, step=100,
                recursive=True, ignore_permission_denied=True,
            ):
                if self._stop_event.is_set():
                    break
                on_changes(self.path, changes)
        except Exception as exc:
            logger.warning(f"Directory watch on '{self.path}' stopped with error: {exc}")
        finally:
            _deregister(self.path)
            logger.info(f"Stopped watching {self.path}")


def _deregister(path: str) -> None:
    with _lock:
        _active.pop(path, None)


def on_changes(path: str, changes: set) -> None:
    """Handle one debounced batch of changes: log + desktop notification."""
    count = len(changes)
    lines = []
    for change, p in sorted(changes, key=lambda c: c[1])[:MAX_NOTIFY_PATHS]:
        label = _CHANGE_LABELS.get(int(change), "changed")
        lines.append(f"{label}: {os.path.relpath(p, path)}")
    body = "\n".join(lines)
    if count > MAX_NOTIFY_PATHS:
        body += f"\n… and {count - MAX_NOTIFY_PATHS} more"
    logger.info(f"[watch {path}] {count} change(s):\n{body}")
    name = os.path.basename(path.rstrip("/")) or path
    send_notification("Nexa file watch", f"{name}: {count} change(s)\n{body}")


def start_watch(path: str) -> tuple[bool, str]:
    """Start watching a directory. Returns (ok, message)."""
    path = os.path.abspath(os.path.expanduser(path))
    with _lock:
        if path in _active:
            return False, f"Already watching {path}"
        watch = DirWatch(path)
        _active[path] = watch
        watch.start()
    return True, f"Watching {path} — you'll get a desktop notification on changes (until Nexa exits)."


def stop_watch(path: str | None = None) -> tuple[int, str]:
    """Stop one watch (by path) or all watches. Returns (count_stopped, message)."""
    with _lock:
        if path:
            norm = os.path.abspath(os.path.expanduser(path))
            targets = [w for p, w in _active.items() if p == norm]
        else:
            targets = list(_active.values())
        for w in targets:
            _active.pop(w.path, None)
    for w in targets:
        w.stop()
    if not targets:
        if path:
            return 0, f"Not watching {path}."
        return 0, "No active watches."
    n = len(targets)
    return n, f"Stopped {n} watch(es)." if not path else f"Stopped watching {path}."


def list_watches() -> list[str]:
    with _lock:
        return sorted(_active.keys())


def stop_all_watches() -> None:
    """Stop every active watch (called on shutdown / tests)."""
    stop_watch(None)
