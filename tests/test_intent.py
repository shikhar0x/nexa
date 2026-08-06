import unittest
from runtime.intent import IntentRouter, IntentResult


class TestIntentRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_system_status_intent(self):
        res = self.router.classify("how's my battery?")
        self.assertEqual(res.intent_name, "SYSTEM_STATUS")

        res2 = self.router.classify("what's my CPU usage like?")
        self.assertEqual(res2.intent_name, "SYSTEM_STATUS")

    def test_file_search_intent(self):
        res = self.router.classify("find my latest DBMS presentation")
        self.assertEqual(res.intent_name, "FILE_SEARCH")
        self.assertEqual(res.args.get("query"), "dbms presentation")

    def test_file_content_search_intent(self):
        res = self.router.classify("search inside files for TODO")
        self.assertEqual(res.intent_name, "FILE_CONTENT_SEARCH")

    def test_reminder_intent(self):
        res = self.router.classify("remind me in 30 seconds to take a break")
        self.assertEqual(res.intent_name, "SET_REMINDER")
        self.assertEqual(res.args.get("delay_seconds"), 30)
        self.assertEqual(res.args.get("message"), "take a break")

    def test_open_file_intent(self):
        res = self.router.classify("open /tmp/test.txt")
        self.assertEqual(res.intent_name, "OPEN_FILE")
        self.assertEqual(res.args.get("path"), "/tmp/test.txt")

    def test_run_command_intent(self):
        res = self.router.classify("run command ls -la")
        self.assertEqual(res.intent_name, "RUN_COMMAND")
        self.assertEqual(res.args.get("command"), "ls -la")

    def test_general_fallback_intent(self):
        res = self.router.classify("what is 2 + 2?")
        self.assertEqual(res.intent_name, "GENERAL")


if __name__ == "__main__":
    unittest.main()
