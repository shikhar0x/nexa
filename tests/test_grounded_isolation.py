"""Regression tests for grounded-turn memory isolation.

Live-observed failure: user asked "what project am i working on?", the answer
fell through to memory chat, the wrong answer was stored, and every retry of
the same question regurgitated that stored answer verbatim ("The content
provided does not specify a project name or details.") — a self-poisoning
echo loop. Grounded (allow_interpretation) turns must never see conversation
history or the retrieved-memory block.
"""

import unittest
from unittest.mock import patch

from runtime.context import ConversationContext
from runtime.llm import LLMEngine
from skills.base import SkillResult


def _make_engine() -> LLMEngine:
    with patch.object(LLMEngine, "_ensure_model_exists", lambda self: None):
        return LLMEngine(model_name="test-model")


def _chat_recorder(captured: list):
    def fake_chat(model, messages, stream, **kwargs):
        captured.extend(dict(m) for m in messages)
        return iter([{"message": {"content": "ok"}}])
    return fake_chat


ECHO_ANSWER = "The content provided does not specify a project name or details."


class TestGroundedTurnIsolation(unittest.TestCase):
    def test_grounded_turn_drops_history_and_memory_block(self):
        engine = _make_engine()
        ctx = ConversationContext(
            user_input="what project am i working on?",
            memory_context="RETRIEVED MEMORY: earlier answer — " + ECHO_ANSWER,
            recent_history=[
                {"role": "user", "content": "what project am i working on?"},
                {"role": "assistant", "content": ECHO_ANSWER},
            ],
            skill_result=SkillResult(
                success=True,
                data={"Project or workspace": "nexa"},
                message="The user's focused window belongs to Visual Studio Code.",
                use_llm=True,
                allow_interpretation=True,
            ),
        )
        captured: list = []
        with patch("runtime.llm.ollama.chat", _chat_recorder(captured)):
            out = "".join(engine.stream(ctx))

        self.assertEqual(out, "ok")
        roles = [m["role"] for m in captured]
        self.assertEqual(roles, ["system", "user"])  # no replayed history
        system = captured[0]["content"]
        self.assertIn("Project or workspace", system)      # the facts are there
        self.assertNotIn("RETRIEVED MEMORY", system)       # the poison is not
        self.assertNotIn(ECHO_ANSWER, str(captured))       # nowhere in any message

    def test_general_turn_keeps_history_and_memory_block(self):
        engine = _make_engine()
        ctx = ConversationContext(
            user_input="what did we talk about?",
            memory_context="RETRIEVED MEMORY BLOCK",
            recent_history=[{"role": "assistant", "content": "earlier answer"}],
            skill_result=None,
        )
        captured: list = []
        with patch("runtime.llm.ollama.chat", _chat_recorder(captured)):
            "".join(engine.stream(ctx))

        self.assertEqual([m["role"] for m in captured], ["system", "assistant", "user"])
        self.assertIn("RETRIEVED MEMORY BLOCK", captured[0]["content"])

    def test_non_interpreted_tool_turn_keeps_context(self):
        # use_llm results WITHOUT interpretation are plain chat augmentation;
        # only strictly-grounded turns are isolated.
        engine = _make_engine()
        ctx = ConversationContext(
            user_input="q",
            memory_context="RETRIEVED MEMORY BLOCK",
            recent_history=[{"role": "assistant", "content": "earlier answer"}],
            skill_result=SkillResult(
                success=True,
                message="raw tool output",
                use_llm=True,
                allow_interpretation=False,
            ),
        )
        captured: list = []
        with patch("runtime.llm.ollama.chat", _chat_recorder(captured)):
            "".join(engine.stream(ctx))

        self.assertEqual([m["role"] for m in captured], ["system", "assistant", "user"])
        self.assertIn("RETRIEVED MEMORY BLOCK", captured[0]["content"])


if __name__ == "__main__":
    unittest.main()
