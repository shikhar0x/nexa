import os
import unittest
from runtime.context import ConversationContext
from runtime.dispatcher import Dispatcher
from skills.base import SkillResult
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.system_status import SystemStatusSkill
from skills.os_info import OSInfoSkill
from skills.network_info import NetworkInfoSkill
from skills.process_info import ProcessInfoSkill
from skills.directory_listing import DirectoryListingSkill
from skills.unsupported import UnsupportedCapabilitySkill
from skills.file_reader import FileReaderSkill
from infrastructure.services.system_status import SystemStatusService
from infrastructure.services.os_info import OSInfoService
from infrastructure.services.network_info import NetworkInfoService
from infrastructure.services.process_info import ProcessInfoService
from infrastructure.services.directory_listing import DirectoryListingService
from config.settings import settings


class TestArchitecture(unittest.TestCase):
    def setUp(self):
        self.context = ConversationContext(user_input="test")
        self.registry = SkillRegistry()
        self.registry.register(SystemStatusSkill())
        self.registry.register(OSInfoSkill())
        self.registry.register(NetworkInfoSkill())
        self.registry.register(ProcessInfoSkill())
        self.registry.register(DirectoryListingSkill())
        self.registry.register(UnsupportedCapabilitySkill())
        self.resolver = CapabilityResolver(registry=self.registry)

    def test_services_layer(self):
        sys_data = SystemStatusService().get_status()
        self.assertIsNotNone(sys_data.cpu_name)

        os_data = OSInfoService().get_info()
        self.assertIsNotNone(os_data.os_distro)
        self.assertIsNotNone(os_data.hostname)

        net_data = NetworkInfoService().get_info()
        self.assertIsNotNone(net_data.local_ip)

        proc_data = ProcessInfoService().get_info(top_n=3)
        self.assertGreaterEqual(proc_data.total_processes, 1)

        dir_data = DirectoryListingService().list_directory(os.getcwd())
        self.assertGreaterEqual(dir_data.total_items, 1)

    def test_capability_metadata(self):
        skill = OSInfoSkill()
        self.assertEqual(skill.capability.name, "os_info")
        self.assertIn("kernel", skill.capability.supports)

    def test_capability_resolver_single_and_fanout(self):
        # Single skill match
        os_skills = self.resolver.resolve("SYSTEM_INFO", "show os version")
        self.assertEqual(len(os_skills), 1)
        self.assertEqual(os_skills[0].name, "OS_INFO")

        net_skills = self.resolver.resolve("SYSTEM_INFO", "what is my ip")
        self.assertEqual(len(net_skills), 1)
        self.assertEqual(net_skills[0].name, "NETWORK_INFO")

        # Full report fanout aggregation match
        full_skills = self.resolver.resolve("SYSTEM_INFO", "give me a complete system report")
        self.assertEqual(len(full_skills), 3)
        skill_names = [s.name for s in full_skills]
        self.assertIn("SYSTEM_STATUS", skill_names)
        self.assertIn("OS_INFO", skill_names)
        self.assertIn("NETWORK_INFO", skill_names)

    def test_unsupported_capability_skill(self):
        skill = UnsupportedCapabilitySkill()
        res = skill.execute({"query": "quantum teleportation"}, self.context)
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("I don't currently have a native Python capability", res.message)

    def test_directory_listing_skill(self):
        skill = DirectoryListingSkill()
        res = skill.execute({"path": "."}, self.context)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)
        self.assertTrue(res.allow_interpretation)
        self.assertIn("target_path", res.data)

    def test_debug_instrumentation(self):
        settings.debug = True
        dispatcher = Dispatcher()
        dispatcher.initialize()
        # Verify execution trace doesn't crash
        result_text = dispatcher.process("show os version")
        self.assertIsNotNone(result_text)
        settings.debug = False


if __name__ == "__main__":
    unittest.main()
