"""
Hybrid intent classifier: deterministic keyword router first, supervised
LLM fallback second.

Architecture note: this is a drop-in implementation of the existing
BaseIntentClassifier interface. The rest of the pipeline (Dispatcher,
CapabilityResolver, skills, memory, safety gate) consumes only the
IntentResult DTO and is completely unaware of this class.
"""
from typing import Optional

from runtime.intent import BaseIntentClassifier, IntentResult, IntentRouter
from runtime.llm import LLMEngine
from config.constants import LLM_CLASSIFIABLE_INTENTS
from config.logger import logger


class HybridIntentClassifier(BaseIntentClassifier):
    """
    Wraps the deterministic IntentRouter. When the keyword router falls back
    to GENERAL, the local LLM (the same single model used for chat) is asked
    to pick one of Nexa's known capabilities. The suggestion is validated
    against the LLM_CLASSIFIABLE_INTENTS whitelist and its args are extracted
    by the router's deterministic extractors — so the model can never trigger
    an intent outside the whitelist, and never decides arguments itself.
    """

    def __init__(
        self,
        router: Optional[IntentRouter] = None,
        llm: Optional[LLMEngine] = None,
        fallback_enabled: bool = True,
    ) -> None:
        self.router = router or IntentRouter()
        self.llm = llm or LLMEngine()
        self.fallback_enabled = fallback_enabled

    def classify(self, user_input: str) -> IntentResult:
        # 1. Deterministic keyword router always runs first
        result = self.router.classify(user_input)
        if result.intent_name != "GENERAL" or not self.fallback_enabled:
            return result

        # 2. LLM fallback only for messages the router did not understand
        suggestion = self.llm.classify_intent(user_input)
        if not suggestion:
            return result

        intent_name = suggestion.get("intent")
        # Whitelist check: model can only suggest known, safe capabilities
        if intent_name not in LLM_CLASSIFIABLE_INTENTS or intent_name == "GENERAL":
            logger.debug(
                f"LLM suggested '{intent_name}' — not in whitelist; keeping GENERAL"
            )
            return result

        # 3. Args are always extracted by the deterministic router logic
        args = self.router.extract_args(intent_name, user_input)
        logger.debug(f"LLM fallback classified '{user_input}' -> {intent_name} args={args}")
        return IntentResult(intent_name=intent_name, args=args, confidence=0.6)
