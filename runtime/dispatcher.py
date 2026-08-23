import time
from typing import Optional, Any

from runtime.context import ConversationContext
from runtime.intent import IntentRouter, BaseIntentClassifier
from runtime.llm import LLMEngine
from runtime.renderer import ConsoleRenderer
from skills.base import BaseSkill, SkillResult
from skills.build_log import BuildLogSkill
from skills.repo_index import RepoIndexSkill
from skills.file_watch import FileWatchSkill
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.system_status import SystemStatusSkill
from skills.os_info import OSInfoSkill
from skills.network_info import NetworkInfoSkill
from skills.process_info import ProcessInfoSkill
from skills.directory_listing import DirectoryListingSkill
from skills.time_date import TimeDateSkill
from skills.screenshot import ScreenshotSkill
from skills.active_window import ActiveWindowSkill
from skills.work_context import WorkContextSkill
from skills.git import GitSkill
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


from runtime.clarification import ClarificationResolver


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
        self.clarification_resolver = ClarificationResolver()
        self.workspace_state: dict[str, Any] = {}
        self.current_context: Optional[ConversationContext] = None

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
        self.registry.register(TimeDateSkill())
        self.registry.register(ScreenshotSkill())
        self.registry.register(ActiveWindowSkill())
        self.registry.register(WorkContextSkill())
        self.registry.register(GitSkill())
        self.registry.register(BuildLogSkill())
        self.registry.register(RepoIndexSkill())
        self.registry.register(FileWatchSkill())
        # Repo-index intents map to RepoIndexSkill
        repo_skill = self.registry.get("REPO_INDEX")
        for ri_intent in ("REPO_INDEX",):
            self.registry.register_alias(ri_intent, repo_skill)

        # Git intents map to the GitSkill (not memory!)
        git_skill = self.registry.get("GIT")
        for git_intent in ("GIT_STATUS", "GIT_BRANCH", "GIT_DIFF", "GIT_LOG", "GIT_ADD", "GIT_COMMIT", "GIT_ADD_COMMIT", "GIT_CHECKOUT"):
            self.registry.register_alias(git_intent, git_skill)

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
            "MEMORY_DATE",
        ):
            self.registry.register_alias(intent_name, mem_skill)

    def process(self, user_input: str, context: Optional[ConversationContext] = None) -> str:
        """Process a single turn of user input through the system pipeline."""
        start_time = time.time()
        logger.info(f"Processing turn for input: '{user_input}'")

        # 1. Reuse or create conversation context (enabling stateless dispatcher operation)
        if context is None:
            if self.current_context is None:
                self.current_context = ConversationContext(user_input=user_input)
            else:
                self.current_context.user_input = user_input
            context = self.current_context
        else:
            context.user_input = user_input

        # Check pending action timeout
        if context.pending_action and getattr(context.pending_action, "timestamp", None):
            elapsed = time.time() - context.pending_action.timestamp
            if elapsed > settings.pending_action_timeout:
                if settings.debug:
                    logger.debug(f"[DEBUG TRACE] PendingAction expired (elapsed {round(elapsed, 1)}s > {settings.pending_action_timeout}s)")
                context.pending_action = None

        # 2. Intent Recognition via abstract classifier
        intent = self.router.classify(user_input)
        context.conversation_state["intent"] = intent.intent_name
        context.workspace_state = self.workspace_state.copy()

        # 3. Handle Pending Action Clarification Resolution
        if context.pending_action:
            pending = context.pending_action

            # Explicit cancellation check
            if self.clarification_resolver.is_cancellation(user_input):
                if settings.debug:
                    logger.debug(f"[DEBUG TRACE] PendingAction cleared by explicit user cancellation: {pending.skill_name}")
                context.pending_action = None
                rendered = self.renderer.render_static("Cancelled.")
                self.memory.store_exchange(user_input, "Cancelled.")
                return rendered

            # New explicit tool workflow clears pending action
            if intent.intent_name not in ("GENERAL", "DIRECTORY_LISTING", "FILE_SEARCH"):
                if settings.debug:
                    logger.debug(f"[DEBUG TRACE] PendingAction cleared due to new tool workflow '{intent.intent_name}'")
                context.pending_action = None
            else:
                # Attempt clarification resolution
                resolved_args = self.clarification_resolver.resolve(user_input, pending.missing_args, context)
                if resolved_args is not None:
                    if settings.debug:
                        logger.debug(f"[DEBUG TRACE] Resolved PendingAction clarification: {resolved_args}")
                        logger.debug(f"[DEBUG TRACE] Re-executing pending skill: '{pending.skill_name}'")

                    pending.args.update(resolved_args)
                    pending.args.pop("ask_folder", None)
                    pending.args.pop("ask_directory", None)
                    pending.args.pop("require_folder", None)
                    pending_skill = self.registry.get(pending.skill_name)
                    if pending_skill:
                        result = pending_skill.execute(pending.args, context)
                        context.pending_action = result.pending_action
                        context.skill_result = result
                        self.workspace_state.update(context.workspace_state)

                        if result.pending_action and settings.debug:
                            logger.debug(f"[DEBUG TRACE] Created PendingAction: skill={result.pending_action.skill_name}, missing_args={result.pending_action.missing_args}")

                        if not result.use_llm:
                            rendered = self.renderer.render_static(result.message)
                            self.memory.store_exchange(user_input, result.message)
                            self._log_debug_trace(user_input, intent.intent_name, [pending_skill], result, start_time, False)
                            return rendered
                elif intent.intent_name == "GENERAL":
                    if settings.debug:
                        logger.debug(f"[DEBUG TRACE] Intermediate GENERAL query; retaining active PendingAction '{pending.skill_name}'")

        # 4. Retrieve persistent memory context (for non-memory intents)
        if not intent.intent_name.startswith("MEMORY_"):
            context.memory_context = self.memory.get_context(user_input)

        # 5. Resolve capability skills dynamically
        matched_skills = self.resolver.resolve(intent.intent_name, user_input)
        llm_invoked = True

        if matched_skills:
            if len(matched_skills) == 1:
                skill = matched_skills[0]
                logger.info(f"Executing resolved skill '{skill.name}' for intent '{intent.intent_name}'")
                result = skill.execute(intent.args, context)
            else:
                # Multi-Skill Fan-Out Aggregation
                logger.info(f"Fan-out aggregating skills {[s.name for s in matched_skills]} for intent '{intent.intent_name}'")
                aggregated_data = {}
                messages = []
                success = True
                use_llm = True
                allow_interp = True
                pending_act = None
                any_skill_wants_llm = False

                for skill in matched_skills:
                    res = skill.execute(intent.args, context)
                    if not res.success:
                        success = False
                    if not res.use_llm:
                        use_llm = False
                    if not res.allow_interpretation:
                        allow_interp = False
                    if res.use_llm:
                        any_skill_wants_llm = True
                    if res.pending_action:
                        pending_act = res.pending_action
                    aggregated_data[skill.name.lower()] = res.data
                    if res.message:
                        messages.append(res.message)

                # Explanation override: if ANY fan-out skill wants the LLM
                # (e.g. explicit "explain each term"), honor it — otherwise
                # a deterministic OS/network report would suppress the
                # explanation for the whole aggregated result.
                if any_skill_wants_llm:
                    use_llm = True
                    allow_interp = True

                result = SkillResult(
                    success=success,
                    data=aggregated_data,
                    message="\n\n".join(messages),
                    use_llm=use_llm,
                    allow_interpretation=allow_interp,
                    pending_action=pending_act,
                )

            context.skill_result = result
            context.pending_action = result.pending_action
            if result.pending_action and settings.debug:
                logger.debug(f"[DEBUG TRACE] Created PendingAction: skill={result.pending_action.skill_name}, missing_args={result.pending_action.missing_args}")

            self.workspace_state.update(context.workspace_state)

            # Deterministic skills or static bypass
            if not result.use_llm:
                llm_invoked = False
                rendered = self.renderer.render_static(result.message)
                self.memory.store_exchange(user_input, result.message)
                self._log_debug_trace(user_input, intent.intent_name, matched_skills, result, start_time, llm_invoked)
                return rendered

        # 6. LLM Response Generation
        context.recent_history = self.memory.get_recent_conversation(limit=settings.history_limit)
        chunk_generator = self.llm.stream(context)
        response = self.renderer.render_stream(chunk_generator)

        # 7. Store exchange & update workspace state
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

