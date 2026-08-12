import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.context import ConversationContext
from runtime.intent import IntentRouter
from runtime.dispatcher import Dispatcher


PROMPTS_FILE = Path(__file__).parent / "prompts.json"


class TestPromptRegressions(unittest.TestCase):
    """
    JSON-driven prompt regression test runner for Nexa.
    Loads tests/prompts.json fixtures and validates intent classification,
    argument extraction, skill resolution, and dispatcher execution.
    """

    @classmethod
    def setUpClass(cls):
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)

    def setUp(self):
        self.router = IntentRouter()
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()

    def test_json_prompt_fixtures(self):
        """Run subtest assertions for every fixture in tests/prompts.json."""
        for fixture in self.fixtures:
            prompt_input = fixture["input"]
            expected_intent = fixture["expected_intent"]
            expected_skill = fixture["expected_skill"]
            expected_args = fixture.get("expected_args_subset")

            with self.subTest(prompt=prompt_input, expected_intent=expected_intent):
                # 1. Test Intent Classification
                intent_res = self.router.classify(prompt_input)
                self.assertEqual(
                    intent_res.intent_name,
                    expected_intent,
                    f"Prompt '{prompt_input}' classified as '{intent_res.intent_name}', expected '{expected_intent}'",
                )

                # 2. Test Non-GENERAL Actionable Prompts
                if expected_intent != "GENERAL":
                    self.assertNotEqual(
                        intent_res.intent_name,
                        "GENERAL",
                        f"Actionable prompt '{prompt_input}' unexpectedly fell back to GENERAL",
                    )

                # 3. Test Argument Extraction Subset
                if expected_args:
                    for key, val in expected_args.items():
                        self.assertIn(key, intent_res.args)
                        self.assertEqual(
                            intent_res.args[key],
                            val,
                            f"Prompt '{prompt_input}' arg '{key}'={intent_res.args[key]}, expected '{val}'",
                        )

                # 4. Test Skill Resolution
                if expected_skill != "GENERAL":
                    matched_skills = self.dispatcher.resolver.resolve(intent_res.intent_name, prompt_input)
                    self.assertTrue(
                        matched_skills,
                        f"No skills resolved for intent '{intent_res.intent_name}' (prompt: '{prompt_input}')",
                    )
                    skill_names = [s.name for s in matched_skills]
                    self.assertTrue(
                        any(s == expected_skill or s.startswith(expected_skill) for s in skill_names),
                        f"Resolved skills {skill_names} do not contain expected '{expected_skill}' for prompt '{prompt_input}'",
                    )

                # 5. Test End-to-End Dispatcher Processing under mock stream & security gates
                with patch("skills.shell.confirm_action", return_value=True), \
                     patch("skills.open_file.confirm_action", return_value=True), \
                     patch("skills.brightness.confirm_action", return_value=True), \
                     patch("skills.volume.confirm_action", return_value=True), \
                     patch("skills.wifi.confirm_action", return_value=True), \
                     patch("skills.power.confirm_action", return_value=True), \
                     patch("infrastructure.security.confirm_action", return_value=True), \
                     patch("infrastructure.os.os_adapter.run_command", return_value=MagicMock(returncode=0, stdout="mocked output", stderr="")), \
                     patch("infrastructure.os.os_adapter.set_brightness", return_value={"level": 80}), \
                     patch("infrastructure.os.os_adapter.set_volume", return_value={"level": 50}), \
                     patch.object(self.dispatcher.llm, "stream", return_value=iter(["Mocked response"])):
                    response = self.dispatcher.process(prompt_input)
                    self.assertTrue(response, f"Dispatcher returned empty response for prompt '{prompt_input}'")


if __name__ == "__main__":
    unittest.main()
