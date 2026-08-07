import unittest
from runtime.context import ConversationContext
from skills.base import SkillResult, BaseSkill
from skills.registry import SkillRegistry
from skills.system_status import SystemStatusSkill
from skills.file_search import FileSearchSkill
from skills.notification import ReminderSkill


class TestSkills(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry()
        self.context = ConversationContext(user_input="test")

    def test_registry_registration(self):
        skill = SystemStatusSkill()
        self.registry.register(skill)
        self.assertEqual(self.registry.get("SYSTEM_STATUS"), skill)
        self.assertIn("SYSTEM_STATUS", self.registry.list_skills())

    def test_system_status_skill(self):
        skill = SystemStatusSkill()
        result = skill.execute({}, self.context)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertIn("cpu_percent", result.data)
        self.assertTrue(result.use_llm)
        self.assertTrue(result.allow_interpretation)

    def test_file_search_skill(self):
        skill = FileSearchSkill()
        result = skill.execute({"query": "main.py"}, self.context)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertIn("results", result.data)
        self.assertTrue(result.use_llm)
        self.assertTrue(result.allow_interpretation)

    def test_reminder_skill(self):
        skill = ReminderSkill()
        result = skill.execute({"delay_seconds": 10, "message": "test reminder"}, self.context)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("delay_seconds"), 10)
        self.assertFalse(result.use_llm)
        self.assertFalse(result.allow_interpretation)


if __name__ == "__main__":
    unittest.main()

