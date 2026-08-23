import os
import unittest
from unittest.mock import patch

from config.settings import Settings, settings


class TestStorageIsolation(unittest.TestCase):
    """Settings must honor env overrides, and the suite must never touch real memory."""

    def test_settings_honor_env_overrides(self):
        with patch.dict(os.environ, {"NEXA_DB_PATH": "/tmp/nexa-iso-check.db",
                                     "NEXA_CHROMA_PATH": ":memory:"}):
            s = Settings()
        self.assertEqual(s.db_path, "/tmp/nexa-iso-check.db")
        self.assertEqual(s.chroma_path, ":memory:")

    def test_suite_never_uses_repo_real_memory(self):
        # Regression guard: if tests/conftest.py is bypassed, this fails loudly
        # instead of silently poisoning the developer's real memory again.
        self.assertNotEqual(settings.db_path, "nexa.db")
        self.assertIn("nexa-test-data-", settings.db_path)
        self.assertEqual(settings.chroma_path, ":memory:")


if __name__ == "__main__":
    unittest.main()
