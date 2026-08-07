from typing import Any
from skills.base import BaseSkill, SkillResult, Capability


class UnsupportedCapabilitySkill(BaseSkill):
    """Fallback skill for user requests asking for unsupported system capabilities."""

    name = "UNSUPPORTED_CAPABILITY"
    description = "Handles queries for system features not natively provided by Nexa skills."
    permissions = []
    capability = Capability(
        name="unsupported_capability",
        description="Gracefully rejects unsupported system capabilities and offers shell execution",
        supports=["unsupported"],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        query = args.get("query", context.user_input)
        message = (
            f"I don't currently have a native Python capability for '{query}'. "
            "Would you like me to run a shell command for you?"
        )
        return SkillResult(
            success=False,
            data={"status": "unsupported", "query": query},
            message=message,
            use_llm=False,  # Strictly bypass LLM to prevent hallucinated tool responses
        )
