from dataclasses import dataclass, field
from typing import Any, Optional

from config.settings import settings


def deterministic_report_flags() -> tuple[bool, bool]:
    """Return (use_llm, allow_interpretation) for factual info skills."""
    if settings.deterministic_system_report:
        return False, False
    return True, True



@dataclass
class Capability:
    """Metadata describing skill capability, supported features, and security rules."""
    name: str
    description: str
    supports: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    deterministic: bool = False


@dataclass
class PendingAction:
    """Represents a skill execution requiring user clarification / missing arguments."""
    skill_name: str
    args: dict[str, Any] = field(default_factory=dict)
    missing_args: list[str] = field(default_factory=list)
    prompt: str = ""
    timestamp: float = 0.0


@dataclass
class SkillResult:
    """Standardized result returned by all Nexa skills."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    use_llm: bool = True  # If False, Dispatcher returns message directly without calling LLMEngine
    allow_interpretation: bool = False  # If True, LLM may interpret trusted structured data under strict grounding rules
    pending_action: Optional[PendingAction] = None


class BaseSkill:
    """Base class for all skills in Nexa."""
    name: str = "base_skill"
    description: str = "Base skill interface"
    permissions: list[str] = field(default_factory=list)
    capability: Capability = Capability(name="base_skill", description="Base skill capability")

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        """
        Execute the skill with the given arguments and conversation context.
        Must return a standardized SkillResult.
        """
        raise NotImplementedError

    def on_event(self, event: Any) -> None:
        """Optional hook for event-driven triggers (Event-Bus ready)."""
        pass

