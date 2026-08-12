import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import settings
from runtime.context import ConversationContext
from skills.directory_listing import DirectoryListingSkill
from skills.file_reader import FileReaderSkill
from skills.path_resolver import (
    resolve_filename_or_path,
    set_active_directory,
    get_active_directory,
)


class TestFix7FilesystemWorkingContext(unittest.TestCase):
    """
    Test suite for Phase 2 Stabilization Fix #7: Filesystem Working Context.
    Uses temporary directories and controllable mocks.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

        self.dir1 = self.base_path / "Downloads"
        self.dir2 = self.base_path / "Documents"
        self.dir1.mkdir(parents=True, exist_ok=True)
        self.dir2.mkdir(parents=True, exist_ok=True)

        self.file1 = self.dir1 / "report.pdf"
        self.file2 = self.dir2 / "report.pdf"

        self.file1.write_text("Downloads report content")
        self.file2.write_text("Documents report content")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_successful_directory_listing_sets_working_directory(self):
        """Verify successful directory listing records active_directory and timestamp."""
        context = ConversationContext(user_input="List Downloads")
        skill = DirectoryListingSkill()

        res = skill.execute({"path": str(self.dir1)}, context)
        self.assertTrue(res.success)
        self.assertEqual(context.workspace_state.get("active_directory"), str(self.dir1))
        self.assertIsNotNone(context.workspace_state.get("active_directory_timestamp"))

    def test_successful_read_sets_parent_working_directory(self):
        """Verify successful file read records file parent directory as active_directory."""
        context = ConversationContext(user_input="read report.pdf")
        skill = FileReaderSkill()

        with patch.object(skill, "_read_pdf", return_value="PDF text"):
            res = skill.execute({"path": str(self.file1)}, context)
            self.assertTrue(res.success)
            self.assertEqual(context.workspace_state.get("active_directory"), str(self.dir1))
            self.assertEqual(context.workspace_state.get("active_file"), str(self.file1))

    def test_filename_only_lookup_prefers_working_directory(self):
        """Verify filename-only operations search working directory first."""
        context = ConversationContext(user_input="read report.pdf")
        set_active_directory(context, self.dir1)

        status, resolved = resolve_filename_or_path(
            "report.pdf", context=context
        )
        self.assertEqual(status, "EXACT")
        self.assertEqual(resolved, self.file1)

    def test_explicit_folder_overrides_working_directory(self):
        """Verify explicit search_dirs/path overrides working directory."""
        context = ConversationContext(user_input="read report.pdf from Documents")
        set_active_directory(context, self.dir1)

        # Explicit search_dirs=[self.dir2] overrides working directory self.dir1
        status, resolved = resolve_filename_or_path(
            "report.pdf", context=context, search_dirs=[self.dir2]
        )
        self.assertEqual(status, "EXACT")
        self.assertEqual(resolved, self.file2)

    def test_expired_context_is_ignored(self):
        """Verify get_active_directory returns None when timestamp exceeds working_directory_timeout."""
        context = ConversationContext(user_input="test")
        set_active_directory(context, self.dir1)

        # Simulate elapsed time beyond timeout
        old_timestamp = time.time() - (settings.working_directory_timeout + 10.0)
        context.workspace_state["active_directory_timestamp"] = old_timestamp

        active_path = get_active_directory(context)
        self.assertIsNone(active_path)

    def test_failed_operations_do_not_replace_good_working_context(self):
        """Verify failed operations (e.g. missing file) preserve existing working context."""
        context = ConversationContext(user_input="read missing.txt")
        set_active_directory(context, self.dir1)
        original_dir = context.workspace_state.get("active_directory")

        skill = FileReaderSkill()
        res = skill.execute({"path": "non_existent_file.txt"}, context)
        self.assertFalse(res.success)

        # Working context must remain unchanged
        self.assertEqual(context.workspace_state.get("active_directory"), original_dir)

    def test_pronoun_followup_preserves_active_file(self):
        """Verify pronoun follow-up ('summarize it') uses active_file without regression."""
        context = ConversationContext(user_input="summarize it")
        context.workspace_state["active_file"] = str(self.file1)

        skill = FileReaderSkill()
        with patch.object(skill, "_read_pdf", return_value="PDF text"):
            res = skill.execute({"path": "it"}, context)
            self.assertTrue(res.success)
            self.assertEqual(res.data.get("path"), str(self.file1))


if __name__ == "__main__":
    unittest.main()
