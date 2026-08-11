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
            self.assertEqual(res.data.get("query"), "dbms")
            self.assertIn(mock_file, res.data.get("results"))
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
                self.assertIn(mock_content_file, res.data.get("results"))


if __name__ == "__main__":
    unittest.main()
