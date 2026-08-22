"""
Hybrid intent classifier: deterministic keyword router first, supervised
LLM fallback second.

Architecture note: this is a drop-in implementation of the existing
BaseIntentClassifier interface. The rest of the pipeline (Dispatcher,
CapabilityResolver, skills, memory, safety gate) consumes only the
IntentResult DTO and is completely unaware of this class.
"""
import re
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

# "What can you do?" style questions should stay GENERAL so the system
# prompt's capability list answers them — never routed to a specific skill.
CAPABILITY_QUESTIONS = (
    "what can you do", "what can u do", "what are your skills",
    "what are your abilities", "list your abilities", "list your skills",
    "list down all of your abilities", "list down all your abilities",
    "list your capabilities", "list your capabilities",
    "what are you capable of", "what are you capable of doing",
    "what do you do", "what all can you do", "what all can u do",
    "what are all your features", "what features do you have",
    "what are your features", "your skills", "your abilities",
    "show me your skills", "tell me your skills",
    "what can you help me with", "how can you help me",
    "what are you", "who are you", "introduce yourself",
    "tell me about yourself",
)

# Short conversational follow-ups ("why?", "how?", "really?") that must
# stay GENERAL and never trigger a skill or a classification call.
SHORT_FOLLOWUPS = (
    "why", "how", "really", "hmm", "huh", "ok", "okay", "and", "so",
    "then", "wait", "which", "is it", "does it", "can it", "should i",
    "do i", "what", "when", "where", "who",
    "explain it", "explain it to me", "explain that", "explain this",
    "explain the above", "explain the above response", "explain the above answer",
    "explain what that means", "what does that mean", "what does it mean",
    "what do you mean", "summarize it", "summarize that", "read it",
    "read that", "tell me more", "go on", "continue", "more details",
    "a bit more", "give me an example", "like what",
)

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
        if text in SMALL_TALK_EXACT or text.startswith(SMALL_TALK_PREFIXES):
            return True
        # Capability questions ("what can you do?") also stay GENERAL.
        # Word-boundary match: 'so' must not match inside 'something'.
        if any(re.search(rf"\b{re.escape(q)}\b", text) for q in CAPABILITY_QUESTIONS):
            return True
        # Short conversational follow-ups ("why?", "how?") stay GENERAL too
        if text in SHORT_FOLLOWUPS:
            return True
        return False

    def classify(self, user_input: str) -> IntentResult:
        # 1. Deterministic keyword router always runs first
        result = self.router.classify(user_input)
        # Git intents (GIT_STATUS/LOG/DIFF/...) are deterministic router
        # results — always pass through, never LLM-classified or rejected.
        if result.intent_name.startswith("GIT_"):
            return result
        if result.intent_name != "GENERAL" or not self.fallback_enabled:
            return result

        # 2. Obvious chit-chat ("hey there!", "thanks", "why?") answers
        #    directly as GENERAL — no classification call, no double model
        #    latency, and never a misrouted skill.
        if self._is_small_talk(user_input):
            logger.debug(f"Small-talk fast path for '{user_input}'; skipping LLM classification")
            return result

        # 3. LLM fallback only for messages the router did not understand
        suggestion = self.llm.classify_intent(user_input)
        if not suggestion:
            return result

        intent_name = suggestion.get("intent")
        # Whitelist check: model can only suggest capabilities from the
        # index — and never destructive intents (belt and suspenders: the
        # index already excludes them, this guards against future edits).
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
