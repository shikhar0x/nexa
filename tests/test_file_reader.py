import unittest
import os
import tempfile

from runtime.context import ConversationContext
from skills.file_reader import FileReaderSkill
from skills.base import SkillResult
from runtime.intent import IntentRouter
from runtime.dispatcher import Dispatcher
from memory.vector_store import reset_vector_store
from config.settings import settings


class TestFileReaderSkill(unittest.TestCase):
    def setUp(self):
        settings.db_path = "test_file_reader.db"
        settings.chroma_path = ":memory:"
        reset_vector_store()
        self.skill = FileReaderSkill()
        self.context = ConversationContext(user_input="test")
        self.router = IntentRouter()

    def tearDown(self):
        reset_vector_store()
        if os.path.exists(settings.db_path):
            os.remove(settings.db_path)
        settings.db_path = "nexa.db"
        settings.chroma_path = "chroma_data"
        reset_vector_store()

    def test_read_txt_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("Hello Nexa! This is test content.")
            temp_path = f.name

        try:
            result = self.skill.execute({"path": temp_path}, self.context)
            self.assertIsInstance(result, SkillResult)
            self.assertTrue(result.success)
            self.assertTrue(result.use_llm)  # Extracted text uses LLM for analysis
            self.assertIn("Hello Nexa!", result.message)
            self.assertEqual(os.path.realpath(self.context.workspace_state.get("active_file")), os.path.realpath(temp_path))
        finally:
            os.remove(temp_path)

    def test_read_nonexistent_file_deterministic_error(self):
        result = self.skill.execute({"path": "/tmp/non_existent_file_9999.txt"}, self.context)
        self.assertIsInstance(result, SkillResult)
        self.assertFalse(result.success)
        self.assertFalse(result.use_llm)  # Deterministic error bypasses LLM!
        self.assertIn("File does not exist", result.message)

    def test_file_read_intent_classification(self):
        intent = self.router.classify("what are the contents of /home/shikhar/test.pdf")
        self.assertEqual(intent.intent_name, "FILE_READ")
        self.assertEqual(intent.args.get("path"), "/home/shikhar/test.pdf")

    def test_workspace_active_file_resolution(self):
        self.context.workspace_state["active_file"] = "/tmp/sample.txt"
        intent = self.router.classify("summarize this file")
        self.assertEqual(intent.intent_name, "FILE_READ")

        result = self.skill.execute({"path": "active_file"}, self.context)
        # Should attempt to read /tmp/sample.txt
        self.assertFalse(result.success)
        self.assertIn("/tmp/sample.txt", result.message)


if __name__ == "__main__":
    unittest.main()
