import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.context import ConversationContext
from runtime.dispatcher import Dispatcher
from skills.file_reader import FileReaderSkill
from skills.open_file import OpenFileSkill
from skills.path_resolver import resolve_filename_or_path, resolve_path
from infrastructure.search.oswalk import OsWalkSearchBackend


class TestAutomaticFilenameResolution(unittest.TestCase):
    def setUp(self):
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()

    def test_explicit_path_remains_unchanged(self):
        """Requirement 1: Existing explicit paths work unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "explicit_file.txt"
            f.write_text("Hello Explicit")
            status, res = resolve_filename_or_path(str(f))
            self.assertEqual(status, "EXACT")
            self.assertEqual(res, f.resolve())

    def test_single_unique_filename_match(self):
        """Requirement 2 & 4: Single unique filename match resolves automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            downloads = base / "Downloads"
            downloads.mkdir()
            report = downloads / "report.pdf"
            report.write_text("%PDF-1.4 Mock content")

            backend = OsWalkSearchBackend()
            with patch("skills.path_resolver.SPECIAL_FOLDERS", {
                "downloads": downloads,
                "desktop": base / "Desktop",
                "documents": base / "Documents",
                "home": base,
            }):
                with patch("infrastructure.search.oswalk.PRIORITY_DIRS", [str(downloads)]):
                    status, res = resolve_filename_or_path("report.pdf", backend=backend)
                    self.assertEqual(status, "EXACT")
                    self.assertEqual(res, report.resolve())

    def test_missing_filename_returns_factual_error(self):
        """Requirement 5: Missing filename returns deterministic factual error without calling LLM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            backend = OsWalkSearchBackend()
            with patch("skills.path_resolver.SPECIAL_FOLDERS", {
                "downloads": base / "Downloads",
                "desktop": base / "Desktop",
                "documents": base / "Documents",
                "home": base,
            }):
                with patch("infrastructure.search.oswalk.PRIORITY_DIRS", []):
                    skill = FileReaderSkill()
                    context = ConversationContext(user_input="summarize missing.pdf")
                    res = skill.execute({"path": "missing.pdf"}, context)

                    self.assertFalse(res.success)
                    self.assertFalse(res.use_llm)
                    self.assertIn("File does not exist", res.message)

    def test_duplicate_filename_produces_numbered_choices_and_pending_action(self):
        """Requirement 6: Duplicate filenames present a numbered choice list and set PendingAction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            dir1 = base / "Downloads"
            dir2 = base / "Documents"
            dir1.mkdir()
            dir2.mkdir()

            f1 = dir1 / "notes.docx"
            f2 = dir2 / "notes.docx"
            f1.write_text("Notes 1")
            f2.write_text("Notes 2")

            backend = OsWalkSearchBackend()
            with patch("skills.path_resolver.SPECIAL_FOLDERS", {
                "downloads": dir1,
                "desktop": base / "Desktop",
                "documents": dir2,
                "home": base,
            }):
                with patch("infrastructure.search.oswalk.PRIORITY_DIRS", [str(dir1), str(dir2)]):
                    skill = FileReaderSkill()
                    context = ConversationContext(user_input="read notes.docx")
                    res = skill.execute({"path": "notes.docx"}, context)

                    self.assertFalse(res.success)
                    self.assertFalse(res.use_llm)
                    self.assertIsNotNone(res.pending_action)
                    self.assertEqual(res.pending_action.skill_name, "FILE_READ")
                    self.assertIn("1.", res.message)
                    self.assertIn("2.", res.message)
                    self.assertIn(str(f1.resolve()), res.message)
                    self.assertIn(str(f2.resolve()), res.message)

    def test_follow_up_selection_executes_original_pending_operation(self):
        """Requirement 7: Follow-up choice '1' executes original pending operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            dir1 = base / "Downloads"
            dir2 = base / "Documents"
            dir1.mkdir()
            dir2.mkdir()

            f1 = dir1 / "notes.txt"
            f2 = dir2 / "notes.txt"
            f1.write_text("Content of file 1")
            f2.write_text("Content of file 2")

            skill = FileReaderSkill()
            context = ConversationContext(user_input="read notes.txt")

            with patch("skills.path_resolver.SPECIAL_FOLDERS", {
                "downloads": dir1,
                "desktop": base / "Desktop",
                "documents": dir2,
                "home": base,
            }):
                with patch("infrastructure.search.oswalk.PRIORITY_DIRS", [str(dir1), str(dir2)]):
                    # Turn 1: Triggers choices prompt & pending action
                    res1 = skill.execute({"path": "notes.txt"}, context)
                    context.pending_action = res1.pending_action

                    # Turn 2: User selects option "1"
                    turn2_output = self.dispatcher.process("1", context=context)
                    self.assertIsNone(context.pending_action)
                    self.assertIsNotNone(context.skill_result)
                    self.assertTrue(context.skill_result.success)
                    self.assertIn("Content of file 1", context.skill_result.message)

    def test_active_directory_takes_priority_over_known_folders(self):
        """Requirement 3: Active directory from context takes priority over known folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            active_dir = base / "ActiveWork"
            downloads = base / "Downloads"
            active_dir.mkdir()
            downloads.mkdir()

            f_active = active_dir / "project-plan.pdf"
            f_downloads = downloads / "project-plan.pdf"
            f_active.write_text("Active plan")
            f_downloads.write_text("Downloads plan")

            context = ConversationContext(user_input="summarize project-plan.pdf")
            context.workspace_state["active_directory"] = str(active_dir)

            backend = OsWalkSearchBackend()
            with patch("skills.path_resolver.SPECIAL_FOLDERS", {
                "downloads": downloads,
                "desktop": base / "Desktop",
                "documents": base / "Documents",
                "home": base,
            }):
                with patch("infrastructure.search.oswalk.PRIORITY_DIRS", [str(downloads)]):
                    status, res = resolve_filename_or_path("project-plan.pdf", context=context, backend=backend)
                    self.assertEqual(status, "EXACT")
                    self.assertEqual(res, f_active.resolve())

    def test_open_file_skill_preserves_safety_confirmation(self):
        """Validation: Preserve safety confirmation for OpenFileSkill after resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            f = base / "document.pdf"
            f.write_text("PDF content")

            skill = OpenFileSkill()
            context = ConversationContext(user_input="open document.pdf")

            with patch("skills.open_file.resolve_filename_or_path", return_value=("EXACT", f)):
                with patch("skills.open_file.confirm_action", return_value=False) as mock_confirm:
                    res = skill.execute({"path": "document.pdf"}, context)
                    mock_confirm.assert_called_once()
                    self.assertFalse(res.success)
                    self.assertIn("Cancelled", res.message)

                with patch("skills.open_file.resolve_filename_or_path", return_value=("EXACT", f)):
                    with patch("skills.open_file.confirm_action", return_value=True):
                        with patch("skills.open_file.os_adapter.open_file") as mock_open:
                            res_ok = skill.execute({"path": "document.pdf"}, context)
                            mock_open.assert_called_once_with(str(f))
                            self.assertTrue(res_ok.success)
                            self.assertIn("Opened", res_ok.message)


if __name__ == "__main__":
    unittest.main()
