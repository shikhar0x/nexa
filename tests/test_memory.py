import unittest
import os
from memory.service import MemoryService
from memory.vector_store import reset_vector_store
from config.settings import settings


class TestMemoryService(unittest.TestCase):
    def setUp(self):
        settings.db_path = "test_nexa.db"
        settings.chroma_path = ":memory:"
        reset_vector_store()
        self.memory = MemoryService()
        self.memory.initialize()

    def tearDown(self):
        reset_vector_store()
        if os.path.exists(settings.db_path):
            os.remove(settings.db_path)
        settings.db_path = "nexa.db"
        settings.chroma_path = "chroma_data"
        reset_vector_store()

    def test_store_and_retrieve_memory(self):
        self.memory.store_exchange("I love coding in Python", "I'll remember that your favorite color is green.")
        context = self.memory.get_context("Python")
        self.assertTrue(len(context) > 0)


if __name__ == "__main__":
    unittest.main()
