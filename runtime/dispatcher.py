from typing import Optional

from runtime.context import ConversationContext
from runtime.intent import IntentRouter
from runtime.llm import LLMEngine
from skills.registry import SkillRegistry
from skills.system_status import SystemStatusSkill
from skills.file_search import FileSearchSkill, FileContentSearchSkill
from skills.open_file import OpenFileSkill
from skills.shell import ShellExecutionSkill
from skills.notification import ReminderSkill
from memory.service import MemoryService
from infrastructure.scheduler import Scheduler
from config.logger import logger


class Dispatcher:
    """
    Central runtime orchestrator driving Nexa execution flow:
    User Input -> IntentRouter -> SkillRegistry -> Skill -> Context -> LLM -> Memory -> Response
    """

    def __init__(
        self,
        router: Optional[IntentRouter] = None,
        registry: Optional[SkillRegistry] = None,
        llm: Optional[LLMEngine] = None,
        memory: Optional[MemoryService] = None,
        scheduler: Optional[Scheduler] = None,
    ) -> None:
        self.router = router or IntentRouter()
        self.registry = registry or SkillRegistry()
        self.llm = llm or LLMEngine()
        self.memory = memory or MemoryService()
        self.scheduler = scheduler or Scheduler()

    def initialize(self) -> None:
        """Initialize databases, logger, and register default skills."""
        logger.info("Initializing Dispatcher runtime...")
        self.memory.initialize()
        self._register_default_skills()
        logger.info(f"Dispatcher initialized with skills: {self.registry.list_skills()}")

    def _register_default_skills(self) -> None:
        self.registry.register(SystemStatusSkill())
        self.registry.register(FileSearchSkill())
        self.registry.register(FileContentSearchSkill())
        self.registry.register(OpenFileSkill())
        self.registry.register(ShellExecutionSkill())
        self.registry.register(ReminderSkill(scheduler=self.scheduler))

    def process(self, user_input: str) -> str:
        """Process a single turn of user input through the system pipeline."""
        logger.info(f"Processing turn for input: '{user_input}'")

        # 1. Intent Recognition
        intent = self.router.classify(user_input)

        # 2. Context creation
        context = ConversationContext(user_input=user_input)

        # 3. Retrieve persistent memory context
        context.memory_context = self.memory.get_context(user_input)

        # 4. Dispatch to skill if registered
        skill = self.registry.get(intent.intent_name)
        if skill:
            logger.info(f"Executing skill '{skill.name}' with args {intent.args}")
            result = skill.execute(intent.args, context)
            context.skill_result = result

            if intent.intent_name in ("OPEN_FILE", "RUN_COMMAND"):
                self.memory.store_exchange(user_input, result.message)
                return f"{result.message}"

        # 5. LLM Natural Language Generation
        response = self.llm.generate(context)

        # 6. Store turn exchange in memory
        self.memory.store_exchange(user_input, response)

        logger.info(f"Turn processed successfully. Response length: {len(response)} chars")
        return response
