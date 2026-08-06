import unittest
import os
import shutil
from memory.service import MemoryService
from config.settings import settings


class TestMemoryService(unittest.TestCase):
    def setUp(self):
        settings.db_path = "test_nexa.db"
        settings.chroma_path = "test_chroma_data"
        self.memory = MemoryService()
        self.memory.initialize()

    def tearDown(self):
        if os.path.exists(settings.db_path):
            os.remove(settings.db_path)
        if os.path.exists(settings.chroma_path):
            shutil.rmtree(settings.chroma_path)
        settings.db_path = "nexa.db"
        settings.chroma_path = "chroma_data"

    def test_store_and_retrieve_memory(self):
        self.memory.store_exchange("My favorite color is green", "I'll remember that your favorite color is green.")
        context = self.memory.get_context("favorite color")
        self.assertTrue(len(context) > 0)


if __name__ == "__main__":
    unittest.main()
