from dataclasses import dataclass, field
from typing import Any, Optional
from skills.base import SkillResult, PendingAction


@dataclass
class ConversationContext:
    """Central context object containing conversation and environment state."""
    user_input: str
    memory_context: str = ""
    skill_result: Optional[SkillResult] = None
    recent_history: list[dict[str, Any]] = field(default_factory=list)
    system_state: dict[str, Any] = field(default_factory=dict)
    workspace_state: dict[str, Any] = field(default_factory=dict)
    user_state: dict[str, Any] = field(default_factory=dict)
    conversation_state: dict[str, Any] = field(default_factory=dict)
    pending_action: Optional[PendingAction] = None


    def format_for_llm(self) -> str:
        """Format skill results and structured context into a prompt string for the LLM."""
        if not self.skill_result:
            return ""

        sections = []

        if self.skill_result.allow_interpretation:
            sections.append("=== TRUSTED TOOL DATA GROUNDING (ALLOW_INTERPRETATION = TRUE) ===")
            if self.skill_result.data:
                formatted_pairs = []
                for k, v in self.skill_result.data.items():
                    val_str = "Unavailable (None)" if v is None else str(v)
                    formatted_pairs.append(f"  - {k}: {val_str}")
                sections.append("Structured Sensor & Tool Key-Value Measurements:\n" + "\n".join(formatted_pairs))

            if self.skill_result.message:
                sections.append(f"Tool Diagnostic Summary:\n{self.skill_result.message}")
        else:
            if self.skill_result.message:
                sections.append(f"Real-time Data / Tool Output:\n{self.skill_result.message}")
            elif self.skill_result.data:
                formatted_data = "\n".join(f"  - {k}: {v}" for k, v in self.skill_result.data.items())
                sections.append(f"Real-time Data / Tool Output:\n{formatted_data}")

        return "\n\n".join(sections)

