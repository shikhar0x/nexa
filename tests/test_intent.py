import unittest
from runtime.intent import IntentRouter, IntentResult


class TestIntentRouter(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_system_info_intent(self):
        res = self.router.classify("how's my battery?")
        self.assertEqual(res.intent_name, "SYSTEM_INFO")

        res2 = self.router.classify("what's my CPU usage like?")
        self.assertEqual(res2.intent_name, "SYSTEM_INFO")

        res3 = self.router.classify("give me the stats f the hardware components in exact number")
        self.assertEqual(res3.intent_name, "SYSTEM_INFO")

        res4 = self.router.classify("what do you see?")
        self.assertEqual(res4.intent_name, "SYSTEM_INFO")

        res5 = self.router.classify("check hardware specs")
        self.assertEqual(res5.intent_name, "SYSTEM_INFO")

        res6 = self.router.classify("show os version")
        self.assertEqual(res6.intent_name, "SYSTEM_INFO")

        res7 = self.router.classify("what's my IP?")
        self.assertEqual(res7.intent_name, "SYSTEM_INFO")

    def test_process_info_intent(self):
        res = self.router.classify("list running processes")
        self.assertEqual(res.intent_name, "PROCESS_INFO")

    def test_directory_listing_intent(self):
        res = self.router.classify("list files in Downloads")
        self.assertEqual(res.intent_name, "DIRECTORY_LISTING")

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

    def test_shell_command_routing_regression(self):
        """Verify safety-critical shell command routing precedence and regex word boundary checks."""
        test_cases = [
            ("run intel_gpu_top", "RUN_COMMAND", "intel_gpu_top"),
            ("intel_gpu_top", "RUN_COMMAND", "intel_gpu_top"),
            ("run nvidia-smi", "RUN_COMMAND", "nvidia-smi"),
            ("nvidia-smi", "RUN_COMMAND", "nvidia-smi"),
            ("check gpu usage", "SYSTEM_INFO", None),
            ("gpu usage", "SYSTEM_INFO", None),
            ("run python main.py", "RUN_COMMAND", "python main.py"),
            ("python main.py", "RUN_COMMAND", "python main.py"),
            ("run ls", "RUN_COMMAND", "ls"),
            ("run git status", "RUN_COMMAND", "git status"),
            ("git status", "RUN_COMMAND", "git status"),
            ("run command ls -la", "RUN_COMMAND", "ls -la"),
        ]

        for query, expected_intent, expected_cmd in test_cases:
            res = self.router.classify(query)
            self.assertEqual(
                res.intent_name,
                expected_intent,
                f"Query '{query}' classified as '{res.intent_name}', expected '{expected_intent}'"
            )
            if expected_cmd is not None:
                self.assertEqual(res.args.get("command"), expected_cmd)



    def test_general_fallback_intent(self):
        res = self.router.classify("what is 2 + 2?")
        self.assertEqual(res.intent_name, "GENERAL")

    def test_ambiguous_keywords_general_intent(self):
        res = self.router.classify("explain how photosynthesis works")
        self.assertEqual(res.intent_name, "GENERAL")

        res2 = self.router.classify("summarize the plot of Inception")
        self.assertEqual(res2.intent_name, "GENERAL")

    def test_brightness_control_intent(self):
        res = self.router.classify("get brightness")
        self.assertEqual(res.intent_name, "BRIGHTNESS_CONTROL")
        self.assertEqual(res.args.get("action"), "get")

        res2 = self.router.classify("set brightness to 80%")
        self.assertEqual(res2.intent_name, "BRIGHTNESS_CONTROL")
        self.assertEqual(res2.args.get("action"), "set")
        self.assertEqual(res2.args.get("level"), 80)

    def test_volume_control_intent(self):
        res = self.router.classify("get volume")
        self.assertEqual(res.intent_name, "VOLUME_CONTROL")
        self.assertEqual(res.args.get("action"), "get")

        res2 = self.router.classify("set volume 70%")
        self.assertEqual(res2.intent_name, "VOLUME_CONTROL")
        self.assertEqual(res2.args.get("action"), "set")
        self.assertEqual(res2.args.get("level"), 70)

        res3 = self.router.classify("mute audio")
        self.assertEqual(res3.intent_name, "VOLUME_CONTROL")
        self.assertEqual(res3.args.get("action"), "mute")

    def test_wifi_control_intent(self):
        res = self.router.classify("wifi status")
        self.assertEqual(res.intent_name, "WIFI_CONTROL")

        res2 = self.router.classify("list available networks")
        self.assertEqual(res2.intent_name, "WIFI_CONTROL")
        self.assertEqual(res2.args.get("action"), "list")

        res3 = self.router.classify("turn off wifi")
        self.assertEqual(res3.intent_name, "WIFI_CONTROL")
        self.assertEqual(res3.args.get("action"), "off")

    def test_power_control_intent(self):
        res = self.router.classify("shutdown computer")
        self.assertEqual(res.intent_name, "POWER_CONTROL")
        self.assertEqual(res.args.get("action"), "shutdown")

        res2 = self.router.classify("restart computer")
        self.assertEqual(res2.intent_name, "POWER_CONTROL")
        self.assertEqual(res2.args.get("action"), "restart")


if __name__ == "__main__":
    unittest.main()
