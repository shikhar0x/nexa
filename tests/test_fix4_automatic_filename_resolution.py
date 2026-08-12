import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.context import ConversationContext
from runtime.dispatcher import Dispatcher
from skills.file_reader import FileReaderSkill
from skills.open_file import OpenFileSkill
from skills.path_resolver import resolve_filename_or_path, resolve_path


class TestFix4AutomaticFilenameResolution(unittest.TestCase):
    """
    Test suite for Phase 2 Stabilization Fix #4: Automatic Filename Resolution.
    Uses isolated temporary directories without scanning developer's home directory.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Create mock directory structure
        self.dir_active = self.base_path / "ActiveWorkspace"
        self.dir_downloads = self.base_path / "Downloads"
        self.dir_desktop = self.base_path / "Desktop"

        self.dir_active.mkdir(parents=True, exist_ok=True)
        self.dir_downloads.mkdir(parents=True, exist_ok=True)
        self.dir_desktop.mkdir(parents=True, exist_ok=True)

        self.search_dirs = [self.dir_active, self.dir_downloads, self.dir_desktop]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_unique_filename_match(self):
        """Verify a single unique filename resolves automatically."""
        sample_file = self.dir_downloads / "report.pdf"
        sample_file.write_text("Sample PDF text content for report.")

        context = ConversationContext(user_input="read report.pdf")
        status, resolved = resolve_filename_or_path(
            "report.pdf", context=context, search_dirs=self.search_dirs
        )

        self.assertEqual(status, "EXACT")
        self.assertEqual(resolved, sample_file)

    def test_duplicate_filename_produces_choice_list(self):
        """Verify multiple matching files produce MULTIPLE status with choice list."""
        file1 = self.dir_downloads / "project-plan.pdf"
        file2 = self.dir_desktop / "project-plan.pdf"

        file1.write_text("Downloads project plan")
        file2.write_text("Desktop project plan")

        context = ConversationContext(user_input="read project-plan.pdf")
        status, choices = resolve_filename_or_path(
            "project-plan.pdf", context=context, search_dirs=self.search_dirs
        )

        self.assertEqual(status, "MULTIPLE")
        self.assertEqual(len(choices), 2)
        self.assertIn(str(file1), choices)
        self.assertIn(str(file2), choices)

    def test_file_reader_skill_duplicate_filename_creates_pending_action(self):
        """Verify FileReaderSkill returns choice prompt and pending_action on duplicate filenames."""
        file1 = self.dir_downloads / "notes.docx"
        file2 = self.dir_desktop / "notes.docx"

        file1.write_text("Notes in downloads")
        file2.write_text("Notes in desktop")

        context = ConversationContext(user_input="read notes.docx")
        skill = FileReaderSkill()

        with patch("skills.file_reader.resolve_filename_or_path", return_value=("MULTIPLE", [str(file1), str(file2)])):
            res = skill.execute({"path": "notes.docx"}, context)

            self.assertFalse(res.success)
            self.assertFalse(res.use_llm)  # Factual response, bypasses LLM
            self.assertIn("1. ", res.message)
            self.assertIn("2. ", res.message)
            self.assertIsNotNone(res.pending_action)
            self.assertEqual(res.pending_action.skill_name, "FILE_READ")
            self.assertEqual(res.pending_action.args.get("choices"), [str(file1), str(file2)])

    def test_missing_filename_returns_deterministic_not_found(self):
        """Verify missing filename returns NOT_FOUND factual response without LLM invocation."""
        context = ConversationContext(user_input="read non_existent_file.txt")
        skill = FileReaderSkill()

        with patch("skills.file_reader.resolve_filename_or_path", return_value=("NOT_FOUND", "non_existent_file.txt")):
            res = skill.execute({"path": "non_existent_file.txt"}, context)

            self.assertFalse(res.success)
            self.assertFalse(res.use_llm)  # Must not invoke LLM
            self.assertIn("File does not exist", res.message)

    def test_active_directory_priority_over_known_folders(self):
        """Verify active_directory in workspace_state takes priority over known folders."""
        file_in_active = self.dir_active / "data.csv"
        file_in_downloads = self.dir_downloads / "data.csv"

        file_in_active.write_text("Active directory data")
        file_in_downloads.write_text("Downloads data")

        context = ConversationContext(user_input="read data.csv")
        context.workspace_state["active_directory"] = str(self.dir_active)

        status, resolved = resolve_filename_or_path(
            "data.csv", context=context, search_dirs=self.search_dirs
        )

        self.assertEqual(status, "EXACT")
        self.assertEqual(resolved, file_in_active)

    def test_open_file_skill_preserves_safety_confirmation(self):
        """Verify OpenFileSkill preserves safety confirmation (confirm_action) after resolving filename."""
        sample_file = self.dir_desktop / "presentation.pdf"
        sample_file.write_text("PDF content")

        context = ConversationContext(user_input="open presentation.pdf")
        skill = OpenFileSkill()

        with patch("skills.open_file.resolve_filename_or_path", return_value=("EXACT", sample_file)):
            with patch("skills.open_file.confirm_action", return_value=False) as mock_confirm:
                res = skill.execute({"path": "presentation.pdf"}, context)

                mock_confirm.assert_called_once()
                self.assertFalse(res.success)
                self.assertIn("Cancelled", res.message)

    def test_followup_number_selection_resolves_pending_operation(self):
        """Verify deterministic follow-up selection ("1") completes pending operation."""
        file1 = self.dir_downloads / "report.txt"
        file2 = self.dir_desktop / "report.txt"

        file1.write_text("Content of report 1")
        file2.write_text("Content of report 2")

        dispatcher = Dispatcher()
        dispatcher.initialize()

        context = ConversationContext(user_input="read report.txt")
        reader_skill = FileReaderSkill()

        # Turn 1: Duplicate filename triggers pending choice
        with patch("skills.file_reader.resolve_filename_or_path", return_value=("MULTIPLE", [str(file1), str(file2)])):
            res1 = reader_skill.execute({"path": "report.txt"}, context)
            context.pending_action = res1.pending_action

        self.assertIsNotNone(context.pending_action)

        # Turn 2: User responds "1"
        with patch.object(dispatcher.llm, "stream", return_value=iter(["Summary of report 1"])):
            output = dispatcher.process("1", context=context)
            self.assertIsNone(context.pending_action)
            self.assertIsNotNone(context.skill_result)
            if context.skill_result is not None:
                res_path = context.skill_result.data.get("path")
                self.assertIsNotNone(res_path)
                self.assertEqual(str(res_path), str(file1))


if __name__ == "__main__":
    unittest.main()
