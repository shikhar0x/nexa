import unittest
from runtime.dispatcher import Dispatcher
from runtime.context import ConversationContext


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()

    def test_dispatcher_initialization(self):
        skills = self.dispatcher.registry.list_skills()
        self.assertIn("SYSTEM_STATUS", skills)
        self.assertIn("FILE_SEARCH", skills)
        self.assertIn("SET_REMINDER", skills)

    def test_intent_classification_routing(self):
        intent = self.dispatcher.router.classify("how is my battery?")
        self.assertEqual(intent.intent_name, "SYSTEM_STATUS")


if __name__ == "__main__":
    unittest.main()
