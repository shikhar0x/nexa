from infrastructure.os import os_adapter


def send_notification(title: str, body: str = "") -> bool:
    """Send an immediate desktop notification via the active OS adapter."""
    return os_adapter.send_notification(title, body)
