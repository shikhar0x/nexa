import threading
from typing import Callable, Any


class Scheduler:
    """Standalone scheduler service for timed jobs, reminders, and future recurring events."""

    def __init__(self) -> None:
        self._timers: list[threading.Timer] = []

    def schedule_once(self, delay_seconds: float, action: Callable[..., Any], *args: Any, **kwargs: Any) -> threading.Timer:
        """Schedule a one-shot task after delay_seconds."""
        timer = threading.Timer(delay_seconds, action, args=args, kwargs=kwargs)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)
        return timer

    def cancel_all(self) -> None:
        """Cancel all pending scheduled tasks."""
        for t in self._timers:
            t.cancel()
        self._timers.clear()
