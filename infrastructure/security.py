"""
Safety gate for OS-modifying actions. Every action that changes system state
must pass through confirm_action(). No exceptions.
"""

def confirm_action(description: str) -> bool:
    """Every OS-modifying action must pass through this. No exceptions."""
    response = input(f"\n⚠ Nexa wants to: {description}\nConfirm? (y/n): ")
    return response.strip().lower() == "y"
