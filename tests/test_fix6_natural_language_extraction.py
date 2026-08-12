import tempfile
import unittest
from pathlib import Path

from runtime.context import ConversationContext
from runtime.intent import IntentRouter
from skills.directory_listing import DirectoryListingSkill
from skills.file_search import FileSearchSkill
from skills.file_reader import FileReaderSkill
from skills.path_resolver import resolve_path, expand_special_folder, SPECIAL_FOLDERS


class TestFix6NaturalLanguageExtraction(unittest.TestCase):
    """
    Subtest-style regression test suite for Phase 2 Stabilization Fix #6:
    Better Natural Language Argument Extraction.
    """

    def setUp(self):
        self.router = IntentRouter()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

        self.dir_downloads = self.base_path / "Downloads"
        self.dir_downloads.mkdir(parents=True, exist_ok=True)
        self.sample_report = self.dir_downloads / "report.pdf"
        self.sample_report.write_text("Dummy PDF content")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_required_folder_phrases(self):
        """Test argument extraction and intent classification for all required folder references."""
        test_cases = [
            ("List files in Downloads", "DIRECTORY_LISTING", "Downloads"),
            ("List files in my downloads", "DIRECTORY_LISTING", "Downloads"),
            ("List files in downloads folder", "DIRECTORY_LISTING", "Downloads"),
            ("Open Desktop", "DIRECTORY_LISTING", "Desktop"),
            ("Open desktop folder", "DIRECTORY_LISTING", "Desktop"),
            ("List files in documents folder", "DIRECTORY_LISTING", "Documents"),
            ("List files in Pictures", "DIRECTORY_LISTING", "Pictures"),
            ("List files in Videos", "DIRECTORY_LISTING", "Videos"),
            ("List files in Music", "DIRECTORY_LISTING", "Music"),
            ("List files in Templates", "DIRECTORY_LISTING", "Templates"),
            ("Show the home directory", "DIRECTORY_LISTING", "home"),
            ("Show the current directory", "DIRECTORY_LISTING", "current"),
            ("List the parent directory", "DIRECTORY_LISTING", "parent"),
            ("Search Documents", "DIRECTORY_LISTING", "Documents"),
        ]
        for prompt, expected_intent, expected_path in test_cases:
            with self.subTest(prompt=prompt):
                res = self.router.classify(prompt)
                self.assertEqual(res.intent_name, expected_intent)
                self.assertEqual(res.args.get("path"), expected_path)

    def test_file_read_search_path_hint_extraction(self):
        """Test extraction of search_path hint for prompts like 'Summarize report.pdf from Downloads'."""
        prompt = "Summarize report.pdf from Downloads"
        res = self.router.classify(prompt)
        self.assertEqual(res.intent_name, "FILE_READ")
        self.assertEqual(res.args.get("path"), "report.pdf")
        self.assertEqual(res.args.get("search_path"), "Downloads")

        # Test FileReaderSkill execution with extracted search_path
        skill = FileReaderSkill()
        context = ConversationContext(user_input=prompt)
        # Patch PyPDF2 reader to return dummy text for test report.pdf
        from unittest.mock import patch
        with patch.object(skill, "_read_pdf", return_value="Extracted PDF text content"):
            skill_res = skill.execute({"path": "report.pdf", "search_path": str(self.dir_downloads)}, context)
            self.assertTrue(skill_res.success)
            self.assertIn("Extracted PDF text content", skill_res.message)

    def test_this_folder_ambiguous_without_active_directory_creates_pending_action(self):
        """Test that 'search this folder' without an active_directory creates pending action rather than guessing."""
        dir_skill = DirectoryListingSkill()
        context = ConversationContext(user_input="list this folder")
        # Ensure active_directory is NOT set in workspace_state
        context.workspace_state.pop("active_directory", None)

        res = dir_skill.execute({"path": "this_folder"}, context)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.pending_action)
        self.assertEqual(res.pending_action.missing_args, ["path"])

        search_skill = FileSearchSkill()
        search_context = ConversationContext(user_input="search this folder")
        search_context.workspace_state.pop("active_directory", None)

        search_res = search_skill.execute({"query": "notes", "search_path": "this_folder"}, search_context)
        self.assertFalse(search_res.success)
        self.assertIsNotNone(search_res.pending_action)
        self.assertEqual(search_res.pending_action.missing_args, ["search_path"])

    def test_this_folder_with_active_directory_resolves_active_directory(self):
        """Test that 'search this folder' with active_directory resolves the active directory context."""
        dir_skill = DirectoryListingSkill()
        context = ConversationContext(user_input="list this folder")
        context.workspace_state["active_directory"] = str(self.base_path)

        res = dir_skill.execute({"path": "this_folder"}, context)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("target_path"), str(self.base_path))

    def test_shell_commands_not_misclassified_as_filesystem_intents(self):
        """Verify safety-sensitive RUN_COMMAND shell commands maintain precedence over filesystem intents."""
        shell_prompts = [
            ("run pwd", "RUN_COMMAND"),
            ("run ls -la", "RUN_COMMAND"),
            ("find . -name '*.pdf'", "RUN_COMMAND"),
            ("execute git status", "RUN_COMMAND"),
        ]
        for prompt, expected_intent in shell_prompts:
            with self.subTest(prompt=prompt):
                res = self.router.classify(prompt)
                self.assertEqual(res.intent_name, expected_intent)


if __name__ == "__main__":
    unittest.main()
