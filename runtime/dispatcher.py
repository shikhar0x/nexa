from typing import Optional, Any

from runtime.context import ConversationContext
from runtime.intent import IntentRouter
from runtime.llm import LLMEngine
from runtime.renderer import ConsoleRenderer
from skills.registry import SkillRegistry
from skills.system_status import SystemStatusSkill
from skills.file_search import FileSearchSkill, FileContentSearchSkill
from skills.file_reader import FileReaderSkill
from skills.open_file import OpenFileSkill
from skills.shell import ShellExecutionSkill
from skills.notification import ReminderSkill
from skills.memory_skill import MemorySkill
from skills.brightness import BrightnessSkill
from skills.volume import VolumeSkill
from skills.wifi import WifiSkill
from skills.power import PowerSkill
from memory.service import MemoryService
from infrastructure.scheduler import Scheduler
from config.logger import logger


class Dispatcher:
    """
    Central runtime orchestrator driving Nexa execution flow:
    User Input -> IntentRouter -> SkillRegistry -> Skill -> Context -> LLM Stream -> Renderer -> Memory
    Maintains lightweight persistent workspace_state (active_file, etc.) across conversation turns.
    """

    def __init__(
        self,
        router: Optional[IntentRouter] = None,
        registry: Optional[SkillRegistry] = None,
        llm: Optional[LLMEngine] = None,
        memory: Optional[MemoryService] = None,
        scheduler: Optional[Scheduler] = None,
        renderer: Optional[ConsoleRenderer] = None,
    ) -> None:
        self.router = router or IntentRouter()
        self.registry = registry or SkillRegistry()
        self.llm = llm or LLMEngine()
        self.memory = memory or MemoryService()
        self.scheduler = scheduler or Scheduler()
        self.renderer = renderer or ConsoleRenderer()
        self.workspace_state: dict[str, Any] = {}

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
        self.registry.register(FileReaderSkill())
        self.registry.register(OpenFileSkill())
        self.registry.register(ShellExecutionSkill())
        self.registry.register(ReminderSkill(scheduler=self.scheduler))
        self.registry.register(BrightnessSkill())
        self.registry.register(VolumeSkill())
        self.registry.register(WifiSkill())
        self.registry.register(PowerSkill())

        # Memory skill handles all memory intents
        mem_skill = MemorySkill(memory_service=self.memory)
        for intent_name in (
            "MEMORY_STATS",
            "MEMORY_LIST",
            "MEMORY_SEARCH",
            "MEMORY_EXPORT",
            "MEMORY_DELETE",
            "MEMORY_CLEAR",
            "MEMORY_SUMMARIZE",
        ):
            self.registry.register_alias(intent_name, mem_skill)

    def process(self, user_input: str) -> str:
        """Process a single turn of user input through the system pipeline."""
        logger.info(f"Processing turn for input: '{user_input}'")

        # 1. Intent Recognition
        intent = self.router.classify(user_input)

        # 2. Context creation & workspace state injection
        context = ConversationContext(user_input=user_input)
        context.conversation_state["intent"] = intent.intent_name
        context.workspace_state = self.workspace_state.copy()

        # 3. Retrieve persistent memory context (for non-memory intents or summarization)
        if not intent.intent_name.startswith("MEMORY_"):
            context.memory_context = self.memory.get_context(user_input)

        # 4. Dispatch to skill if registered
        skill = self.registry.get(intent.intent_name)
        if skill:
            logger.info(f"Executing skill '{skill.name}' (intent '{intent.intent_name}') with args {intent.args}")
            result = skill.execute(intent.args, context)
            context.skill_result = result

            # Persist updated workspace_state across turns (e.g. active_file)
            self.workspace_state.update(context.workspace_state)

            # Deterministic skills or factual errors (use_llm = False) bypass LLM generation
            if not result.use_llm:
                rendered = self.renderer.render_static(result.message)
                self.memory.store_exchange(user_input, result.message)
                logger.info(f"Bypassed LLM generation for intent '{intent.intent_name}' (success={result.success})")
                return rendered

        # 5. Native token streaming LLM response generation via ConsoleRenderer
        chunk_generator = self.llm.stream(context)
        response = self.renderer.render_stream(chunk_generator)

        # 6. Store turn exchange in memory & update workspace state
        self.memory.store_exchange(user_input, response)
        self.workspace_state.update(context.workspace_state)

        logger.info(f"Turn processed successfully. Response length: {len(response)} chars")
        return response
