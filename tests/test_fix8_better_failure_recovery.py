import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.context import ConversationContext
from skills.directory_listing import DirectoryListingSkill
from skills.file_reader import FileReaderSkill
from skills.open_file import OpenFileSkill
from skills.path_resolver import fuzzy_suggest_directory


class TestFix8BetterFailureRecovery(unittest.TestCase):
    """
    Test suite for Phase 2 Stabilization Fix #8: Better Failure Recovery.
    Uses temporary directories and mocked candidate sources.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

        self.dir_downloads = self.base_path / "Downloads"
        self.dir_desktop = self.base_path / "Desktop"
        self.dir_downloads.mkdir(parents=True, exist_ok=True)
        self.dir_desktop.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_downlods_suggests_downloads(self):
        """Verify misspelling 'Downlods' deterministically suggests 'Downloads'."""
        context = ConversationContext(user_input="Open Downlods")
        suggestions = fuzzy_suggest_directory("Downlods", context=context)
        self.assertIn("Downloads", suggestions)

    def test_low_confidence_nonsense_returns_no_fabricated_suggestion(self):
        """Verify nonsense input returns no suggestions."""
        context = ConversationContext(user_input="Open xyz123abc")
        suggestions = fuzzy_suggest_directory("xyz123abc", context=context)
        self.assertEqual(suggestions, [])

    def test_candidate_sources_limited_to_allowed_sources(self):
        """Verify candidates come only from special folders, active directory, or cwd."""
        context = ConversationContext(user_input="Open CustomDirr")
        custom_candidates = [str(self.base_path / "CustomDirectory")]

        suggestions = fuzzy_suggest_directory("CustomDirr", context=context, custom_candidates=custom_candidates)
        self.assertIn("CustomDirectory", suggestions)

    def test_suggested_path_is_not_automatically_opened_or_listed(self):
        """Verify error recovery returns a failure result with suggestions without executing the path."""
        context = ConversationContext(user_input="Open Downlods")
        skill = OpenFileSkill()

        res = skill.execute({"path": "Downlods"}, context)
        # Must fail and prompt user, rather than opening automatically!
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("Did you mean 'Downloads'?", res.message)
        self.assertEqual(res.data.get("error"), "not_found")
        self.assertEqual(res.data.get("attempted_path"), "Downlods")
        self.assertIn("Downloads", res.data.get("suggestions", []))

    def test_existing_valid_paths_continue_to_work(self):
        """Verify existing valid paths proceed normally without error recovery messages."""
        context = ConversationContext(user_input="List Downloads")
        skill = DirectoryListingSkill()

        res = skill.execute({"path": str(self.dir_downloads)}, context)
        self.assertTrue(res.success)
        self.assertNotIn("Did you mean", res.message)


if __name__ == "__main__":
    unittest.main()
