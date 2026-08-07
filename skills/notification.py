from skills.base import BaseSkill, SkillResult, Capability
from infrastructure.scheduler import Scheduler
from infrastructure.notifications import send_notification


class ReminderSkill(BaseSkill):
    """Skill to schedule reminders and trigger desktop notifications."""

    name = "SET_REMINDER"
    description = "Schedules a desktop reminder notification via the Scheduler service."
    permissions = ["SCHEDULE_TASK", "NOTIFY"]
    capability = Capability(
        name="notification",
        description="Schedules a desktop reminder notification via the Scheduler service",
        supports=["reminder", "notify", "set_reminder"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        self.scheduler = scheduler or Scheduler()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        delay_seconds = args.get("delay_seconds", 60)
        message = args.get("message", "Reminder from Nexa")

        # Action to execute when timer fires
        def _on_trigger():
            send_notification("⏰ Nexa Reminder", message)

        self.scheduler.schedule_once(delay_seconds, _on_trigger)

        if delay_seconds >= 3600:
            time_str = f"{delay_seconds // 3600} hour(s)"
        elif delay_seconds >= 60:
            time_str = f"{delay_seconds // 60} minute(s)"
        else:
            time_str = f"{delay_seconds} second(s)"

        user_msg = f"Got it — I'll remind you to '{message}' in {time_str}."
        send_notification("Nexa", f"Reminder set: {message} in {time_str}")

        return SkillResult(
            success=True,
            message=user_msg,
            data={"message": message, "delay_seconds": delay_seconds, "time_str": time_str},
            use_llm=False,
        )

