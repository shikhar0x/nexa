from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SkillResult:
    """Standardized result returned by all Nexa skills."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    use_llm: bool = True  # If False, Dispatcher returns message directly without calling LLMEngine


class BaseSkill:
    """Base class for all skills in Nexa."""
    name: str = "base_skill"
    description: str = "Base skill interface"
    permissions: list[str] = field(default_factory=list)

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        """
        Execute the skill with the given arguments and conversation context.
        Must return a standardized SkillResult.
        """
        raise NotImplementedError

    def on_event(self, event: Any) -> None:
        """Optional hook for event-driven triggers (Event-Bus ready)."""
        pass
