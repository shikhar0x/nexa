import tempfile
import unittest
from pathlib import Path

from skills.path_resolver import (
    resolve_path,
    expand_special_folder,
    expand_relative_path,
    expand_filename,
    validate_exists,
    normalize_directory,
    SPECIAL_FOLDERS,
)
from infrastructure.services.directory_listing import DirectoryListingService
from skills.file_reader import FileReaderSkill
from skills.open_file import OpenFileSkill
from skills.file_search import FileSearchSkill, FileContentSearchSkill
from infrastructure.search.oswalk import OsWalkSearchBackend
from runtime.clarification import ClarificationResolver
from runtime.context import ConversationContext


class TestFix5UnifiedFilesystemUtilities(unittest.TestCase):
    """
    Unit and integration test suite for Phase 2 Stabilization Fix #5: Unified Filesystem Utilities.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

        # Set up isolated directories
        self.dir_docs = self.base_path / "Documents"
        self.dir_downloads = self.base_path / "Downloads"
        self.dir_docs.mkdir(parents=True, exist_ok=True)
        self.dir_downloads.mkdir(parents=True, exist_ok=True)

        self.sample_file = self.dir_docs / "notes.txt"
        self.sample_file.write_text("Hello from notes!")

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Unit Tests for Shared Utility Functions ---

    def test_expand_special_folder(self):
        """Verify lookup of special folders case-insensitively with optional suffixes."""
        self.assertEqual(expand_special_folder("downloads"), SPECIAL_FOLDERS["downloads"])
        self.assertEqual(expand_special_folder("Desktop Folder"), SPECIAL_FOLDERS["desktop"])
        self.assertEqual(expand_special_folder("documents directory"), SPECIAL_FOLDERS["documents"])
        self.assertIsNone(expand_special_folder("invalid_folder_name"))

    def test_normalize_directory(self):
        """Verify normalization of directory paths."""
        normalized = normalize_directory(str(self.dir_docs))
        self.assertEqual(normalized, self.dir_docs)
        self.assertTrue(normalized.is_absolute())

    def test_validate_exists(self):
        """Verify validate_exists returns True for existing paths and False for missing paths."""
        self.assertTrue(validate_exists(self.sample_file))
        self.assertTrue(validate_exists(self.dir_docs))
        fake_file = self.dir_docs / "non_existent.txt"
        self.assertFalse(validate_exists(fake_file))
        self.assertFalse(validate_exists(""))

    def test_expand_relative_path(self):
        """Verify expand_relative_path resolves relative paths against explicit working_dir."""
        rel_path = expand_relative_path("subfolder/file.txt", working_dir=self.base_path)
        self.assertEqual(rel_path, self.base_path / "subfolder" / "file.txt")

    def test_resolve_path_with_special_folder_prefix(self):
        """Verify resolve_path resolves paths with special folder prefixes like Downloads/report.pdf."""
        resolved = resolve_path("Documents/notes.txt")
        expected = SPECIAL_FOLDERS["documents"] / "notes.txt"
        self.assertEqual(resolved, expected)

    def test_expand_filename(self):
        """Verify expand_filename locates files across specified search roots."""
        status, resolved = expand_filename("notes.txt", search_dirs=[self.dir_docs, self.dir_downloads])
        self.assertEqual(status, "EXACT")
        self.assertEqual(resolved, self.sample_file)

    # --- Integration Tests for Consumers ---

    def test_directory_listing_service_integration(self):
        """Verify DirectoryListingService uses shared resolve_path and validate_exists."""
        service = DirectoryListingService()
        data = service.list_directory(str(self.dir_docs))
        self.assertEqual(data.target_path, str(self.dir_docs))
        self.assertEqual(data.total_files, 1)

    def test_clarification_resolver_integration(self):
        """Verify ClarificationResolver resolves special folders and valid paths via shared utilities."""
        resolver = ClarificationResolver()
        context = ConversationContext(user_input="downloads")
        res = resolver.resolve("downloads", ["path"], context)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("path"), str(SPECIAL_FOLDERS["downloads"]))

    def test_file_reader_skill_integration(self):
        """Verify FileReaderSkill uses shared expand_filename and validate_exists."""
        skill = FileReaderSkill()
        context = ConversationContext(user_input="read notes.txt")
        res = skill.execute({"path": str(self.sample_file)}, context)
        self.assertTrue(res.success)
        self.assertIn("Hello from notes!", res.message)

    def test_file_content_search_skill_integration(self):
        """Verify FileContentSearchSkill uses validate_exists for targeted search."""
        skill = FileContentSearchSkill()
        context = ConversationContext(user_input="search notes.txt")
        context.workspace_state["active_file"] = str(self.sample_file)
        res = skill.execute({"query": "Hello", "target_file": str(self.sample_file)}, context)
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
