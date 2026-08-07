from dataclasses import dataclass, field
from typing import Any, Optional
from skills.base import SkillResult


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


    def format_for_llm(self) -> str:
        """Format skill results and context into a prompt string for the LLM."""
        sections = []

        if self.skill_result and self.skill_result.message:
            sections.append(f"Real-time Data / Tool Output:\n{self.skill_result.message}")
        elif self.skill_result and self.skill_result.data:
            formatted_data = "\n".join(f"- {k}: {v}" for k, v in self.skill_result.data.items())
            sections.append(f"Real-time Data / Tool Output:\n{formatted_data}")

        return "\n\n".join(sections)
