from typing import Optional

from runtime.intent import BaseIntentClassifier, IntentResult, IntentRouter
from runtime.llm import LLMEngine
from config.constants import LLM_CLASSIFIABLE_INTENTS
from config.capabilities import DESTRUCTIVE_INTENTS
from config.logger import logger


# Obvious chit-chat that needs no routing and no classification call.
# Safe: this is only consulted AFTER the keyword router already fell back
# to GENERAL, so no destructive intent can ever reach this list.
SMALL_TALK_EXACT = {
    "hi", "hello", "hey", "yo", "sup", "howdy", "hola", "namaste",
    "hi nexa", "hello nexa", "hey nexa", "hi there", "hey there",
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "how are you doing", "how r u", "how are u",
    "how's it going", "how is it going", "what's up", "whats up",
    "wassup", "thank you", "thanks", "thank you nexa", "thanks nexa",
    "bye", "goodbye", "see you", "see ya", "ok", "okay", "cool",
    "nice", "great", "awesome", "nice one", "well done", "good job",
    "lol", "haha", "no problem", "sure", "alright", "perfect",
    "wow", "yes", "no", "yep", "nope", "please",
    "ok thanks", "okay thanks", "k thanks", "thanks a lot", "thanks so much",
    "ok bye", "okay bye", "alright thanks", "ok cool", "okay cool", "nice thanks",
    "thank you so much", "thanks again", "bye bye", "see you later",
}

SMALL_TALK_PREFIXES = (
    "hey ", "hello ", "hi ", "yo ", "howdy", "good morning", "good afternoon",
    "good evening", "good night", "thank you", "thanks", "how are you",
    "how's it going", "what's up", "wassup",
)


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

    @staticmethod
    def _is_small_talk(user_input: str) -> bool:
        text = user_input.strip().lower().rstrip("!.?")
        return text in SMALL_TALK_EXACT or text.startswith(SMALL_TALK_PREFIXES)

    def classify(self, user_input: str) -> IntentResult:
        # 1. Deterministic keyword router always runs first
        result = self.router.classify(user_input)
        if result.intent_name != "GENERAL" or not self.fallback_enabled:
            return result

        # 2. Obvious chit-chat ("hey there!", "thanks") answers directly as
        #    GENERAL — no classification call, no double model latency.
        if self._is_small_talk(user_input):
            logger.debug(f"Small-talk fast path for '{user_input}'; skipping LLM classification")
            return result

        # 3. LLM fallback only for messages the router did not understand
        suggestion = self.llm.classify_intent(user_input)
        if not suggestion:
            return result

        intent_name = suggestion.get("intent")
        # Whitelist check: model can only suggest known, safe capabilities
        if (
            intent_name not in LLM_CLASSIFIABLE_INTENTS
            or intent_name in DESTRUCTIVE_INTENTS
            or intent_name == "GENERAL"
        ):
            logger.debug(
                f"LLM suggested '{intent_name}' — not in whitelist; keeping GENERAL"
            )
            return result

        # 4. Args are always extracted by the deterministic router logic
        args = self.router.extract_args(intent_name, user_input)
        logger.debug(f"LLM fallback classified '{user_input}' -> {intent_name} args={args}")
        return IntentResult(intent_name=intent_name, args=args, confidence=0.6)
