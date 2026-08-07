import os
import unittest
from unittest.mock import MagicMock, patch

from runtime.context import ConversationContext
from runtime.dispatcher import Dispatcher
from runtime.intent import IntentRouter
from skills.resolver import CapabilityResolver
from skills.os_info import OSInfoSkill
from skills.file_search import FileContentSearchSkill, FileSearchSkill
from skills.process_info import ProcessInfoSkill
from skills.directory_listing import DirectoryListingSkill
from infrastructure.services.os_info import OSInfoService
from infrastructure.services.process_info import ProcessInfoService
from infrastructure.monitor import canonicalize_cpu_name, canonicalize_gpu_name
from config.constants import SYSTEM_PROMPT, GROUNDED_INTERPRETATION_PROMPT


class TestPhase2Fixes(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()

    def test_os_info_grounding_and_uptime(self):
        """Goal 1 & 2: Verify OSInfoSkill reads direct Python APIs and calculates uptime."""
        service = OSInfoService()
        info = service.get_info()
        self.assertTrue(info.os_name)
        self.assertTrue(info.kernel_release)
        self.assertTrue(info.hostname)
        self.assertTrue(info.uptime_formatted)
        self.assertGreater(info.uptime_seconds, 0)

        skill = OSInfoSkill(service=service)
        context = ConversationContext(user_input="how long has my computer been running?")
        res = skill.execute({}, context)
        self.assertTrue(res.success)
        self.assertIn(info.os_distro, res.message)
        self.assertIn(info.kernel_release, res.message)
        self.assertIn(info.hostname, res.message)

    def test_directory_listing_path_extraction(self):
        """Goal 3: Verify robust directory path extraction for various phrasing styles."""
        test_cases = [
            ("List files in Downloads", "Downloads"),
            ("Show Desktop", "Desktop"),
            ("List PDFs in Documents", "Documents"),
            ("Show everything inside Pictures", "Pictures"),
            ("Open Downloads", "Downloads"),
            ("How many files are in Music", "Music"),
        ]

        for query, expected_path in test_cases:
            intent = self.router.classify(query)
            self.assertEqual(
                intent.intent_name,
                "DIRECTORY_LISTING",
                f"Query '{query}' classified as '{intent.intent_name}', expected DIRECTORY_LISTING",
            )
            self.assertEqual(
                intent.args.get("path"),
                expected_path,
                f"Query '{query}' extracted path '{intent.args.get('path')}', expected '{expected_path}'",
            )

    def test_file_content_search_no_name_error(self):
        """Goal 4: Verify FileContentSearchSkill executes without NameError: os is not defined."""
        skill = FileContentSearchSkill()
        context = ConversationContext(user_input="search inside file for test")
        
        # Test single file search (active_file present)
        context.workspace_state["active_file"] = __file__
        res = skill.execute({"query": "def test_", "target_file": __file__}, context)
        self.assertTrue(res.success)
        self.assertIn("Found", res.message)

        # Test non-existent file path
        res_nofile = skill.execute({"query": "foo", "target_file": "/nonexistent/path/test.txt"}, context)
        self.assertIsInstance(res_nofile.success, bool)

    def test_process_info_sampling(self):
        """Goal 5: Verify ProcessInfoSkill retrieves non-zero process metrics."""
        service = ProcessInfoService()
        info = service.get_info(top_n=5)
        self.assertGreater(info.total_processes, 0)
        self.assertEqual(len(info.top_cpu_processes), min(5, info.total_processes))
        self.assertEqual(len(info.top_ram_processes), min(5, info.total_processes))

    def test_grounded_prompt_rules(self):
        """Goal 6 & 7 & 9: Verify prompt templates prohibit history leakage and command suggestions."""
        # History leakage prohibition
        self.assertIn("CRITICAL GROUNDING RULE", SYSTEM_PROMPT)
        self.assertIn("ABSOLUTE INDEPENDENCE", GROUNDED_INTERPRETATION_PROMPT)

        # Unnecessary command suggestions prohibition
        self.assertIn("CRITICAL COMMAND RULE", SYSTEM_PROMPT)
        self.assertIn("NO UNNECESSARY COMMANDS", GROUNDED_INTERPRETATION_PROMPT)

    def test_hardware_naming_standardization(self):
        """Goal 8: Verify CPU and GPU naming canonicalization."""
        raw_cpu = "Intel(R) Core(TM) i3-1005G1 CPU @ 1.20GHz"
        clean_cpu = canonicalize_cpu_name(raw_cpu)
        self.assertEqual(clean_cpu, "Intel Core i3-1005G1 CPU @ 1.20GHz")

        raw_gpus = [
            "Intel Corporation Iris Plus Graphics G1 (Ice Lake) (rev 07)",
            "Iris Plus Graphics G1",
            "Intel UHD Graphics",
        ]
        for raw in raw_gpus:
            clean = canonicalize_gpu_name(raw)
            self.assertIn(clean, ("Intel Iris Plus Graphics G1", "Intel UHD Graphics"))

    def test_routing_all_required_queries(self):
        """Goal 10: Verify 11 required system queries route correctly and never fall back to GENERAL."""
        required_queries = [
            ("What's my CPU usage?", "SYSTEM_INFO", "SYSTEM_STATUS"),
            ("What's my system temperature?", "SYSTEM_INFO", "SYSTEM_STATUS"),
            ("What operating system am I running?", "SYSTEM_INFO", "OS_INFO"),
            ("Show my Linux version.", "SYSTEM_INFO", "OS_INFO"),
            ("What's my hostname?", "SYSTEM_INFO", "OS_INFO"),
            ("How long has my computer been running?", "SYSTEM_INFO", "OS_INFO"),
            ("What's my IP address?", "SYSTEM_INFO", "NETWORK_INFO"),
            ("List the top CPU-consuming processes.", "PROCESS_INFO", "PROCESS_INFO"),
            ("List files in Downloads.", "DIRECTORY_LISTING", "DIRECTORY_LISTING"),
            ("Search for files related to DBMS.", "FILE_SEARCH", "FILE_SEARCH"),
            ("Search for SQL inside PDFs.", "FILE_CONTENT_SEARCH", "FILE_CONTENT_SEARCH"),
        ]

        resolver = CapabilityResolver(registry=self.dispatcher.registry)

        for query, expected_intent, expected_skill in required_queries:
            intent = self.router.classify(query)
            self.assertNotEqual(
                intent.intent_name,
                "GENERAL",
                f"Query '{query}' incorrectly fell back to GENERAL",
            )
            self.assertEqual(
                intent.intent_name,
                expected_intent,
                f"Query '{query}' classified as '{intent.intent_name}', expected '{expected_intent}'",
            )

            resolved = resolver.resolve(intent.intent_name, query)
            self.assertTrue(resolved, f"No skills resolved for query '{query}'")
            resolved_names = [s.name for s in resolved]
            self.assertIn(
                expected_skill,
                resolved_names,
                f"Query '{query}' resolved to {resolved_names}, expected {expected_skill}",
            )


if __name__ == "__main__":
    unittest.main()
