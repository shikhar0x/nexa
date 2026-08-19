from datetime import datetime
from typing import Any

from skills.base import BaseSkill, SkillResult, Capability


class TimeDateSkill(BaseSkill):
    """Deterministic instant answers for time/date questions (no model call)."""

    name = "TIME_DATE"
    description = "Answers current time, date, and day-of-week questions deterministically."
    permissions = []
    capability = Capability(
        name="time_date",
        description="Current local time, date, and day of the week",
        supports=["time", "date", "today", "day"],
        requires_confirmation=False,
        deterministic=True,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")
        time_str = now.strftime("%I:%M %p").lstrip("0")

        # Determine what was asked: time-only, date-only, day-only, or all
        query = ""
        if context is not None and hasattr(context, "user_input"):
            query = context.user_input.lower()
        elif args.get("query"):
            query = str(args["query"]).lower()

        time_keywords = ("time", "clock", "hour", "what time")
        date_keywords = ("date", "today", "calendar", "day of week")
        # 'today's date' / 'today' implies the DATE, not time
        wants_day = "day" in query and "date" not in query and "today" not in query

        wants_time = any(k in query for k in time_keywords)
        wants_date = any(k in query for k in date_keywords) or (
            "today" in query and "time" not in query
        )

        if wants_time and not wants_date:
            message = f"It's {time_str}."
        elif wants_day and not wants_time and not wants_date:
            message = f"Today is {day_name}."
        elif wants_date and not wants_time:
            if wants_day:
                message = f"Today is {day_name}, {date_str}."
            else:
                message = f"Today's date is {date_str}."
        else:
            message = f"It's {time_str} on {day_name}, {date_str}."

        return SkillResult(
            success=True,
            data={
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "day": day_name,
            },
            message=message,
            use_llm=False,  # Deterministic, instant
        )
