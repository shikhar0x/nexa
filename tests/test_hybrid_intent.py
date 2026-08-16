import json
import unittest
from unittest.mock import patch

from runtime.intent_hybrid import HybridIntentClassifier


def _fake_response(content: str) -> dict:
    return {"message": {"content": content}}


class TestHybridIntentClassifier(unittest.TestCase):
    """Hybrid router: keyword router first, same-model LLM fallback second."""

    def setUp(self):
        self.classifier = HybridIntentClassifier()

    def test_keyword_router_wins_without_llm_call(self):
        with patch("ollama.chat") as mock_chat:
            res = self.classifier.classify("list files in Downloads")
            self.assertEqual(res.intent_name, "DIRECTORY_LISTING")
            mock_chat.assert_not_called()

    def test_llm_fallback_routes_unrecognized_prompt(self):
        # "which app is heating up my laptop" is not in keyword lists -> GENERAL
        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "PROCESS_INFO"}))):
            res = self.classifier.classify("which app is heating up my laptop")
            self.assertEqual(res.intent_name, "PROCESS_INFO")

    def test_llm_fallback_extracts_args_deterministically(self):
        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "FILE_SEARCH"}))):
            res = self.classifier.classify("i need something about sql anywhere")
            self.assertEqual(res.intent_name, "FILE_SEARCH")
            self.assertIn("query", res.args)
            self.assertTrue(res.args["query"])

    def test_llm_fallback_safe_intent_whitelist(self):
        # Safety-critical intents are NOT in LLM_CLASSIFIABLE_INTENTS
        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "POWER_CONTROL"}))):
            res = self.classifier.classify("switch the machine off")
            self.assertEqual(res.intent_name, "GENERAL")

        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "RUN_COMMAND"}))):
            res = self.classifier.classify("type a command for me")
            self.assertEqual(res.intent_name, "GENERAL")

        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "MEMORY_CLEAR"}))):
            res = self.classifier.classify("erase everything you know")
            self.assertEqual(res.intent_name, "GENERAL")

    def test_llm_suggesting_general_stays_general(self):
        with patch("ollama.chat", return_value=_fake_response(json.dumps({"intent": "GENERAL"}))):
            res = self.classifier.classify("blah blah blah")
            self.assertEqual(res.intent_name, "GENERAL")

    def test_invalid_json_falls_back_to_general(self):
        with patch("ollama.chat", return_value=_fake_response("not json at all")):
            res = self.classifier.classify("blah blah blah")
            self.assertEqual(res.intent_name, "GENERAL")

    def test_fenced_json_is_tolerated(self):
        fenced = "```json\n{\"intent\": \"SYSTEM_INFO\"}\n```"
        with patch("ollama.chat", return_value=_fake_response(fenced)):
            res = self.classifier.classify("what can you tell me about my machine")
            self.assertEqual(res.intent_name, "SYSTEM_INFO")

    def test_ollama_failure_falls_back_to_general(self):
        with patch("ollama.chat", side_effect=Exception("ollama not running")):
            res = self.classifier.classify("blah blah blah")
            self.assertEqual(res.intent_name, "GENERAL")

    def test_fallback_can_be_disabled(self):
        classifier = HybridIntentClassifier(fallback_enabled=False)
        with patch("ollama.chat") as mock_chat:
            res = classifier.classify("which app is heating up my laptop")
            self.assertEqual(res.intent_name, "GENERAL")
            mock_chat.assert_not_called()


if __name__ == "__main__":
    unittest.main()
