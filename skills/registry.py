from typing import Optional
from skills.base import BaseSkill


class SkillRegistry:
    """Registry for managing and looking up Nexa skills."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill instance under its name."""
        self._skills[skill.name] = skill

    def register_alias(self, alias_name: str, skill: BaseSkill) -> None:
        """Register an alternative intent key mapping to a skill instance."""
        self._skills[alias_name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """Retrieve a registered skill by name or alias."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """Return a list of registered skill names."""
        return list(self._skills.keys())
