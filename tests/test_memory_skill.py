import unittest
import os
from unittest.mock import patch

from runtime.context import ConversationContext
from memory.service import MemoryService
from memory.vector_store import reset_vector_store
from skills.memory_skill import MemorySkill
from skills.base import SkillResult
from config.settings import settings


class TestMemorySkill(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = settings.db_path
        self._orig_chroma_path = settings.chroma_path
        settings.db_path = "test_memory_skill.db"
        settings.chroma_path = ":memory:"
        reset_vector_store()
        self.memory = MemoryService()
        self.memory.initialize()
        self.skill = MemorySkill(memory_service=self.memory)

    def tearDown(self):
        reset_vector_store()
        if os.path.exists(settings.db_path):
            os.remove(settings.db_path)
        # Restore the ORIGINAL paths (test-isolated under pytest), never literals.
        settings.db_path = self._orig_db_path
        settings.chroma_path = self._orig_chroma_path
        reset_vector_store()

    def test_memory_stats(self):
        self.memory.store_exchange("I like Python", "Python is great!")
        ctx = ConversationContext(user_input="what do you remember")
        ctx.conversation_state["intent"] = "MEMORY_STATS"

        result = self.skill.execute({}, ctx)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("Total messages logged: 2", result.message)

    def test_memory_export(self):
        self.memory.store_exchange("Test export", "Export response")
        ctx = ConversationContext(user_input="export memory")
        ctx.conversation_state["intent"] = "MEMORY_EXPORT"

        result = self.skill.execute({}, ctx)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        export_path = result.data.get("export_path")
        self.assertIsNotNone(export_path)
        assert isinstance(export_path, str)
        self.assertTrue(os.path.exists(export_path))
        if os.path.exists(export_path):
            os.remove(export_path)

    @patch("skills.memory_skill.confirm_action", return_value=True)
    def test_memory_delete(self, mock_confirm):
        self.memory.store_exchange("My favorite color is green", "Noted green")
        ctx = ConversationContext(user_input="forget color")
        ctx.conversation_state["intent"] = "MEMORY_DELETE"

        result = self.skill.execute({"query": "color"}, ctx)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("Deleted", result.message)
        mock_confirm.assert_called_once_with("delete memories matching 'color'")

    @patch("skills.memory_skill.confirm_action", return_value=False)
    def test_dont_forget_unconfirmed_does_not_delete(self, mock_confirm):
        self.memory.store_exchange("Important note", "Remembering this")
        ctx = ConversationContext(user_input="don't forget to buy milk")
        ctx.conversation_state["intent"] = "MEMORY_DELETE"

        result = self.skill.execute({"query": "don't to buy milk"}, ctx)
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Cancelled — deletion aborted.")
        self.assertEqual(result.data.get("status"), "cancelled")
        stats = self.memory.get_memory_stats()
        self.assertEqual(stats["total_messages"], 2)

    @patch("skills.memory_skill.confirm_action", return_value=True)
    def test_memory_clear(self, mock_confirm):
        self.memory.store_exchange("Item 1", "Item 2")
        ctx = ConversationContext(user_input="clear memory")
        ctx.conversation_state["intent"] = "MEMORY_CLEAR"

        result = self.skill.execute({}, ctx)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        stats = self.memory.get_memory_stats()
        self.assertEqual(stats["total_messages"], 0)

    def test_memory_summarize(self):
        self.memory.store_exchange("Nexa project structure", "Nexa has skills")
        ctx = ConversationContext(user_input="summarize memory about Nexa")
        ctx.conversation_state["intent"] = "MEMORY_SUMMARIZE"

        result = self.skill.execute({"query": "Nexa"}, ctx)
        self.assertTrue(result.success)
        self.assertTrue(result.use_llm)  # Summarization uses LLM!


if __name__ == "__main__":
    unittest.main()
