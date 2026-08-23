from typing import Any

from skills.base import BaseSkill, SkillResult, Capability
from config.logger import logger
from infrastructure.os import os_adapter
from skills.active_window import friendly_app_name, workspace_from_title


class WorkContextSkill(BaseSkill):
    """Answers richer 'what am I doing/working on?' questions.

    Gathers the focused-window facts (including a best-effort project name
    parsed from the window title) and hands them to the LLM
    (use_llm + allow_interpretation) so the answer is phrased naturally,
    grounded in the structured data — unlike the instant template used
    by ActiveWindowSkill for plain 'what app am I using?' queries.
    """

    name = "WORK_CONTEXT"
    description = "Describes what the user is currently working on, phrased naturally by the LLM."
    permissions = []
    capability = Capability(
        name="work_context",
        description="Interpret what the user is currently working on from the focused window",
        supports=[
            "what am i working on",
            "what am i doing right now",
            "what am i looking at",
            "my current activity",
            "what project am i working on",
            "current project",
        ],
        requires_confirmation=False,
        deterministic=False,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        try:
            info = os_adapter.get_active_window()
        except NotImplementedError:
            return SkillResult(
                success=False,
                message="Active-window detection is not supported on this operating system yet, so I can't see what you're working on.",
                data={"error": "not_implemented"},
                use_llm=False,
            )
        except Exception as e:
            logger.warning(f"Work-context probe raised: {e}")
            return SkillResult(
                success=False,
                message=f"I couldn't gather your current activity: {e}",
                data={"error": str(e)},
                use_llm=False,
            )

        if info.get("error"):
            hint = f" {info['hint']}" if info.get("hint") else ""
            return SkillResult(
                success=False,
                message=f"I can't see your current activity: {info['error']}.{hint}".strip(),
                data=info,
                use_llm=False,
            )

        app = (info.get("app") or "").strip()
        title = (info.get("title") or "").strip()
        friendly = friendly_app_name(app)
        project = workspace_from_title(app, title)

        return SkillResult(
            success=True,
            data={
                "Active application": friendly or app or "unreadable",
                "Window title": title or "unreadable",
                "Project or workspace": (
                    project
                    if project
                    else "not identifiable from the window title — say so honestly instead of guessing"
                ),
                "Title pattern": (
                    "editor titles usually read '<file> - <project> - <App Name>'; "
                    "terminal titles usually read 'user@host: <current folder>'"
                ),
                "Window source": info.get("source", "unknown"),
            },
            message=(
                f"The user's focused window belongs to {friendly or app or 'an unknown app'}"
                + (f" and is titled \"{title}\"." if title else " (its title is unreadable).")
            ),
            use_llm=True,
            allow_interpretation=True,
        )
