import time
from typing import Optional, Any

from runtime.context import ConversationContext
from runtime.intent import IntentRouter, BaseIntentClassifier
from runtime.llm import LLMEngine
from runtime.renderer import ConsoleRenderer
from skills.base import BaseSkill, SkillResult
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.system_status import SystemStatusSkill
from skills.os_info import OSInfoSkill
from skills.network_info import NetworkInfoSkill
from skills.process_info import ProcessInfoSkill
from skills.directory_listing import DirectoryListingSkill
from skills.unsupported import UnsupportedCapabilitySkill
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
from config.settings import settings
from config.logger import logger


class Dispatcher:
    """
    Central runtime orchestrator driving Nexa execution flow:
    User Input -> IntentClassifier -> CapabilityResolver -> Skills (Service Layer) -> Context -> LLM -> Renderer -> Memory
    Supports capability-driven skill resolution, generic multi-skill fan-out aggregation, and pipeline debug instrumentation.
    """

    def __init__(
        self,
        router: Optional[BaseIntentClassifier] = None,
        registry: Optional[SkillRegistry] = None,
        resolver: Optional[CapabilityResolver] = None,
        llm: Optional[LLMEngine] = None,
        memory: Optional[MemoryService] = None,
        scheduler: Optional[Scheduler] = None,
        renderer: Optional[ConsoleRenderer] = None,
    ) -> None:
        self.router = router or IntentRouter()
        self.registry = registry or SkillRegistry()
        self.resolver = resolver or CapabilityResolver(registry=self.registry)
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
        self.registry.register(OSInfoSkill())
        self.registry.register(NetworkInfoSkill())
        self.registry.register(ProcessInfoSkill())
        self.registry.register(DirectoryListingSkill())
        self.registry.register(UnsupportedCapabilitySkill())
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
        start_time = time.time()
        logger.info(f"Processing turn for input: '{user_input}'")

        # 1. Intent Recognition via abstract classifier
        intent = self.router.classify(user_input)

        # 2. Context creation & workspace state injection
        context = ConversationContext(user_input=user_input)
        context.conversation_state["intent"] = intent.intent_name
        context.workspace_state = self.workspace_state.copy()

        # 3. Retrieve persistent memory context (for non-memory intents)
        if not intent.intent_name.startswith("MEMORY_"):
            context.memory_context = self.memory.get_context(user_input)

        # 4. Resolve capability skills dynamically (supporting generic fan-out aggregation)
        matched_skills = self.resolver.resolve(intent.intent_name, user_input)
        llm_invoked = True

        if matched_skills:
            if len(matched_skills) == 1:
                skill = matched_skills[0]
                logger.info(f"Executing resolved skill '{skill.name}' for intent '{intent.intent_name}'")
                result = skill.execute(intent.args, context)
            else:
                # Generic Multi-Skill Fan-Out Aggregation
                logger.info(f"Fan-out aggregating skills {[s.name for s in matched_skills]} for intent '{intent.intent_name}'")
                aggregated_data = {}
                messages = []
                success = True
                use_llm = True
                allow_interp = True

                for skill in matched_skills:
                    res = skill.execute(intent.args, context)
                    if not res.success:
                        success = False
                    if not res.use_llm:
                        use_llm = False
                    if not res.allow_interpretation:
                        allow_interp = False
                    aggregated_data[skill.name.lower()] = res.data
                    if res.message:
                        messages.append(res.message)

                result = SkillResult(
                    success=success,
                    data=aggregated_data,
                    message="\n\n".join(messages),
                    use_llm=use_llm,
                    allow_interpretation=allow_interp,
                )

            context.skill_result = result
            self.workspace_state.update(context.workspace_state)

            # Deterministic skills or static bypass (use_llm = False)
            if not result.use_llm:
                llm_invoked = False
                rendered = self.renderer.render_static(result.message)
                self.memory.store_exchange(user_input, result.message)
                self._log_debug_trace(user_input, intent.intent_name, matched_skills, result, start_time, llm_invoked)
                return rendered

        # 5. LLM Response Generation
        context.recent_history = self.memory.get_recent_conversation(limit=6)
        chunk_generator = self.llm.stream(context)
        response = self.renderer.render_stream(chunk_generator)

        # 6. Store exchange & update workspace state
        self.memory.store_exchange(user_input, response)
        self.workspace_state.update(context.workspace_state)

        self._log_debug_trace(user_input, intent.intent_name, matched_skills, context.skill_result, start_time, llm_invoked)
        return response

    def _log_debug_trace(
        self,
        user_input: str,
        intent_name: str,
        matched_skills: list[BaseSkill],
        result: Optional[SkillResult],
        start_time: float,
        llm_invoked: bool,
    ) -> None:
        if settings.debug:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            skill_names = [s.name for s in matched_skills] if matched_skills else ["None"]
            use_llm = result.use_llm if result else True
            allow_interp = result.allow_interpretation if result else False
            print(
                f"\n[DEBUG TRACE]\n"
                f"  USER Input          : '{user_input}'\n"
                f"  Intent Classified   : {intent_name}\n"
                f"  Skills Resolved     : {skill_names}\n"
                f"  Execution Time      : {elapsed_ms} ms\n"
                f"  Result Success      : {result.success if result else True}\n"
                f"  use_llm             : {use_llm}\n"
                f"  allow_interpretation: {allow_interp}\n"
                f"  LLM Invoked?        : {llm_invoked}\n"
                f"[END TRACE]\n"
            )

