import unittest
from unittest.mock import patch

from runtime.intent import IntentRouter
from skills.active_window import workspace_from_title
from skills.work_context import WorkContextSkill
from infrastructure.os import os_adapter


class TestWorkContextRouting(unittest.TestCase):
    """Richer 'what am I doing?' queries must reach WORK_CONTEXT, not ACTIVE_WINDOW."""

    def setUp(self):
        self.router = IntentRouter()

    def test_work_context_phrases(self):
        positives = [
            "what am i working on",
            "what am i working on right now",
            "what am i doing right now",
            "what am i doing?",
            "what am i looking at",
            "what am i reading",
            "what's in front of me",
            "summarize what i'm doing",
            "tell me what i'm doing",
            "which app am i working in",
            # Project-flavoured variants — the live failure was one of these
            # falling through to GENERAL and answering from memory chat.
            "what project am i working on",
            "what project am i working on?",
            "which project am i in",
            "what's the current project",
            "what project is open",
            "what repo am i in",
        ]
        for phrase in positives:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, "WORK_CONTEXT")

    def test_tier_separation(self):
        # Plain identification questions stay on the instant deterministic tier.
        cases = {
            "what app am i using": "ACTIVE_WINDOW",
            "what's the active window": "ACTIVE_WINDOW",
            "which window is focused": "ACTIVE_WINDOW",
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, expected)

    def test_repo_overview_stays_on_repo_index(self):
        # "Explain this project" wants the repo summary skill, not the window.
        cases = [
            "what is this project",
            "what does this project do",
            "explain my project",
            "summarize this repo",
            "tell me about this project",
        ]
        for phrase in cases:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, "REPO_INDEX")


class TestWorkspaceFromTitle(unittest.TestCase):
    """Project/workspace heuristic parsed out of editor & terminal titles."""

    def test_editor_doc_title(self):
        self.assertEqual(
            workspace_from_title("code", "README.md - nexa - Visual Studio Code"),
            "nexa",
        )

    def test_editor_bare_workspace_title(self):
        self.assertEqual(
            workspace_from_title("code", "nexa - Visual Studio Code"),
            "nexa",
        )

    def test_editor_dirty_marker(self):
        self.assertEqual(
            workspace_from_title("code", "● main.py - nexa - Visual Studio Code"),
            "nexa",
        )

    def test_terminal_cwd_title(self):
        self.assertEqual(
            workspace_from_title("gnome-terminal-server", "shikhar@shikhar-ubuntu: ~/Desktop/nexa"),
            "nexa",
        )

    def test_terminal_home_is_not_a_project(self):
        self.assertEqual(
            workspace_from_title("ptyxis", "shikhar@shikhar-ubuntu: ~"),
            "",
        )

    def test_browser_title_gives_nothing(self):
        self.assertEqual(
            workspace_from_title("firefox", "Nexa on GitHub - Mozilla Firefox"),
            "",
        )

    def test_empty_inputs(self):
        self.assertEqual(workspace_from_title("", ""), "")
        self.assertEqual(workspace_from_title("code", ""), "")


class TestWorkContextSkill(unittest.TestCase):
    """Skill must hand structured facts to the LLM (tier 2) or fail gracefully."""

    def setUp(self):
        self.skill = WorkContextSkill()

    def test_success_hands_data_to_llm(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "code", "title": "main.py - nexa - Visual Studio Code",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)
        self.assertTrue(res.allow_interpretation)
        self.assertEqual(res.data["Active application"], "Visual Studio Code")
        self.assertIn("main.py", res.data["Window title"])
        self.assertIn("Visual Studio Code", res.message)

    def test_project_name_grounded_from_editor_title(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "code", "title": "nexa - Visual Studio Code",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertEqual(res.data["Project or workspace"], "nexa")

    def test_project_name_grounded_from_terminal_title(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "gnome-terminal-server",
                                        "title": "shikhar@shikhar-ubuntu: ~/Desktop/nexa",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertEqual(res.data["Project or workspace"], "nexa")

    def test_project_absent_states_honesty_not_guessing(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "firefox",
                                        "title": "Nexa on GitHub - Mozilla Firefox",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertIn("not identifiable", res.data["Project or workspace"])

    def test_error_path_is_deterministic(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"error": "Could not determine the active window",
                                        "hint": "install the extension"}):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("install the extension", res.message)

    def test_not_implemented_is_deterministic(self):
        with patch.object(os_adapter, "get_active_window", side_effect=NotImplementedError):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("not supported", res.message.lower())


if __name__ == "__main__":
    unittest.main()
