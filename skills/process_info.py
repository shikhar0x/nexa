from dataclasses import asdict
from typing import Any
from skills.base import BaseSkill, SkillResult, Capability
from infrastructure.services.process_info import ProcessInfoService


class ProcessInfoSkill(BaseSkill):
    """Thin presentation skill wrapper for running process metrics."""

    name = "PROCESS_INFO"
    description = "Lists total running processes and top CPU/RAM consuming processes."
    permissions = ["READ_PROCESSES"]
    capability = Capability(
        name="process_info",
        description="Reads running processes and top CPU/RAM consuming process items",
        supports=["processes", "process_list", "top_cpu", "top_ram", "ps"],
        requires_confirmation=False,
        deterministic=True,
    )

    def __init__(self, service: ProcessInfoService | None = None) -> None:
        self.service = service or ProcessInfoService()

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        proc_data = self.service.get_info(top_n=5)
        data_dict = asdict(proc_data)

        cpu_lines = [f"  - [{p.pid}] {p.name}: {p.cpu_percent}% CPU, {p.ram_mb} MB RAM" for p in proc_data.top_cpu_processes]
        ram_lines = [f"  - [{p.pid}] {p.name}: {p.ram_mb} MB RAM, {p.cpu_percent}% CPU" for p in proc_data.top_ram_processes]

        message = (
            f"Process Summary ({proc_data.total_processes} total running processes):\n\n"
            f"Top CPU Consuming Processes:\n" + "\n".join(cpu_lines) + "\n\n"
            f"Top RAM Consuming Processes:\n" + "\n".join(ram_lines)
        )

        return SkillResult(
            success=True,
            data=data_dict,
            message=message,
            use_llm=True,
            allow_interpretation=True,
        )
