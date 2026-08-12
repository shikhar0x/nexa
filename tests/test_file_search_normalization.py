import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.context import ConversationContext
from skills.file_search import FileSearchSkill, normalize_file_query
from infrastructure.search.oswalk import OsWalkSearchBackend


class TestFileSearchQueryNormalization(unittest.TestCase):

    def test_query_normalization_filler_words_and_punctuation(self):
        """Verify normalization removes filler words, strips punctuation, and lowercases queries."""
        test_cases = [
            ("Find DBMS files.", "dbms"),
            ("Search for SQL.", "sql"),
            ("Find PDF files.", "pdf"),
            ("Find Telegram reports.", "telegram reports"),
            ("Find files related to SQL.", "sql"),
            ("Search files containing Python.", "python"),
            ("Find my latest DBMS presentation", "dbms presentation"),
        ]
        for raw, expected in test_cases:
            normalized = normalize_file_query(raw)
            self.assertEqual(
                normalized,
                expected,
                f"Query '{raw}' normalized to '{normalized}', expected '{expected}'",
            )

    def test_filename_matching_resource_book_dbms(self):
        """Verify that 'Resource Book DBMS.pdf' matches the query 'Find DBMS files.'"""
        backend = OsWalkSearchBackend()
        raw_query = "Find DBMS files."
        normalized = normalize_file_query(raw_query)
        self.assertEqual(normalized, "dbms")

        # Mock search_filenames_with_stats to return real matching file
        mock_file = str(Path.home() / "Downloads" / "Resource Book DBMS.pdf")
        with patch.object(backend, "search_filenames_with_stats", return_value=([mock_file], 15)):
            skill = FileSearchSkill(backend=backend)
            context = ConversationContext(user_input=raw_query)
            res = skill.execute({"query": raw_query}, context)

            self.assertTrue(res.success)
            self.assertIsNotNone(res.data)
            self.assertEqual(res.data.get("query"), "dbms")
            results = res.data.get("results") or []
            self.assertIn(mock_file, results)
            self.assertIn(mock_file, res.message)

    def test_content_search_fallback_when_zero_filename_matches(self):
        """Verify automatic fallback to content search when filename matches are 0."""
        backend = OsWalkSearchBackend()
        raw_query = "Find files containing secret_passphrase"
        normalized = normalize_file_query(raw_query)
        self.assertEqual(normalized, "secret_passphrase")

        mock_content_file = str(Path.home() / "Documents" / "secrets.txt")
        with patch.object(backend, "search_filenames_with_stats", return_value=([], 50)):
            with patch.object(backend, "search_content_fallback", return_value=[mock_content_file]):
                skill = FileSearchSkill(backend=backend)
                context = ConversationContext(user_input=raw_query)
                res = skill.execute({"query": raw_query}, context)

                self.assertTrue(res.success)
                self.assertIsNotNone(res.data)
                results = res.data.get("results") or []
                self.assertIn(mock_content_file, results)


    def test_recursive_filename_search_and_fuzzy_matching(self):
        """Verify recursive search, arbitrary search root, case insensitivity, and DBMS fuzzy/acronym matching."""
        import tempfile
        backend = OsWalkSearchBackend()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Create nested directory structure
            sub1 = base_dir / "folder1" / "nested"
            sub1.mkdir(parents=True, exist_ok=True)
            
            sub_hidden = base_dir / ".hidden_folder"
            sub_hidden.mkdir(parents=True, exist_ok=True)

            sub_venv = base_dir / "venv" / "lib"
            sub_venv.mkdir(parents=True, exist_ok=True)

            # Create target files
            f1 = sub1 / "Resource Book DBMS.pdf"
            f2 = base_dir / "dbms_notes.docx"
            f3 = sub1 / "Database Management Systems.pdf"
            f4 = sub_hidden / "DBMS_hidden.txt"
            f5 = sub_venv / "dbms_ignored.py"

            for f in (f1, f2, f3, f4, f5):
                f.write_text("sample content")

            # Search with query "DBMS" using custom base_dir
            matches, scanned = backend.search_filenames_with_stats("DBMS", search_path=base_dir)

            match_paths = [Path(m).resolve() for m in matches]

            # f1, f2, and f3 should match
            self.assertIn(f1.resolve(), match_paths)
            self.assertIn(f2.resolve(), match_paths)
            self.assertIn(f3.resolve(), match_paths)

            # Hidden dir and venv dir files should NOT match
            self.assertNotIn(f4.resolve(), match_paths)
            self.assertNotIn(f5.resolve(), match_paths)

    def test_case_insensitive_and_token_search(self):
        """Verify case-insensitive and multi-word token matching across custom search root."""
        import tempfile
        backend = OsWalkSearchBackend()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            sub = base_dir / "reports" / "2026"
            sub.mkdir(parents=True, exist_ok=True)

            f1 = sub / "Telegram_Monthly_Report_Q1.pdf"
            f2 = sub / "unrelated_file.txt"
            f1.write_text("content")
            f2.write_text("content")

            matches = backend.search_filenames("find telegram reports", search_path=base_dir)
            self.assertEqual(len(matches), 1)
            self.assertEqual(Path(matches[0]).resolve(), f1.resolve())


if __name__ == "__main__":
    unittest.main()

