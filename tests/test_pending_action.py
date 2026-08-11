import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.context import ConversationContext
from runtime.dispatcher import Dispatcher
from runtime.clarification import ClarificationResolver
from skills.base import PendingAction, SkillResult
from skills.file_search import FileSearchSkill
from skills.directory_listing import DirectoryListingSkill
from config.settings import settings


class TestPendingActionContinuation(unittest.TestCase):
    def setUp(self):
        self.dispatcher = Dispatcher()
        self.dispatcher.initialize()
        self.dispatcher.llm = MagicMock()
        self.dispatcher.llm.stream = MagicMock(side_effect=lambda ctx: iter(["Mocked LLM Response"]))
        self.resolver = ClarificationResolver()

    def test_clarification_resolver_resolution(self):
        """Test deterministic resolution of missing path/directory arguments."""
        context = ConversationContext(user_input="test")
        
        res_home = self.resolver.resolve("Home directory", ["search_path"], context)
        self.assertEqual(res_home, {"search_path": str(Path.home())})

        res_downloads = self.resolver.resolve("Downloads", ["path"], context)
        self.assertEqual(res_downloads, {"path": str(Path.home() / "Downloads")})

        res_desktop = self.resolver.resolve("Desktop", ["path"], context)
        self.assertEqual(res_desktop, {"path": str(Path.home() / "Desktop")})

        res_here = self.resolver.resolve("here", ["path"], context)
        self.assertEqual(res_here, {"path": str(Path.cwd())})

        res_parent = self.resolver.resolve("parent directory", ["path"], context)
        self.assertEqual(res_parent, {"path": str(Path.cwd().parent)})

    def test_file_search_clarification_flow(self):
        """Test clarification flow after FileSearchSkill."""
        context = ConversationContext(user_input="Find DBMS files.")
        file_skill = FileSearchSkill()
        
        # Turn 1: FileSearchSkill requests directory clarification
        res1 = file_skill.execute({"query": "DBMS", "ask_directory": True}, context)
        self.assertFalse(res1.success)
        self.assertIsNotNone(res1.pending_action)
        self.assertEqual(res1.pending_action.skill_name, "FILE_SEARCH")
        self.assertIn("search_path", res1.pending_action.missing_args)

        context.pending_action = res1.pending_action

        # Turn 2: User provides 'Home directory'
        turn2_output = self.dispatcher.process("Home directory.", context=context)
        self.assertIsNone(context.pending_action)
        self.assertIsNotNone(context.skill_result)
        self.assertIn("DBMS", context.skill_result.message)

    def test_directory_listing_clarification_flow(self):
        """Test clarification flow after DirectoryListingSkill."""
        context = ConversationContext(user_input="List files.")
        dir_skill = DirectoryListingSkill()

        # Turn 1: DirectoryListingSkill requests folder clarification
        res1 = dir_skill.execute({"ask_folder": True}, context)
        self.assertFalse(res1.success)
        self.assertIsNotNone(res1.pending_action)
        self.assertEqual(res1.pending_action.skill_name, "DIRECTORY_LISTING")
        self.assertIn("path", res1.pending_action.missing_args)

        context.pending_action = res1.pending_action

        # Turn 2: User provides 'Downloads'
        turn2_output = self.dispatcher.process("Downloads.", context=context)
        self.assertIsNone(context.pending_action)
        self.assertIsNotNone(context.skill_result)
        self.assertIn("Directory Contents of", context.skill_result.message)

    def test_intermediate_general_query_retains_pending_state(self):
        """Verify an intermediate GENERAL query ('What's 2+2?') returns an answer while retaining pending_action."""
        context = ConversationContext(user_input="List files.")
        dir_skill = DirectoryListingSkill()

        res1 = dir_skill.execute({"ask_folder": True}, context)
        context.pending_action = res1.pending_action
        self.assertIsNotNone(context.pending_action)

        # Turn 2: Intermediate GENERAL query
        with patch.object(self.dispatcher.llm, "stream", return_value=["4"]):
            turn2_output = self.dispatcher.process("What's 2+2?", context=context)
            self.assertEqual(turn2_output, "4")
            # Pending action must be retained for subsequent turn!
            self.assertIsNotNone(context.pending_action)

        # Turn 3: User now provides 'Downloads.'
        turn3_output = self.dispatcher.process("Downloads.", context=context)
        self.assertIsNone(context.pending_action)
        self.assertIsNotNone(context.skill_result)
        self.assertIn("Directory Contents of", context.skill_result.message)

    def test_explicit_cancellation_clears_pending_action(self):
        """Verify explicit cancellation ('never mind' / 'cancel') clears pending action."""
        context = ConversationContext(user_input="List files.")
        dir_skill = DirectoryListingSkill()

        res1 = dir_skill.execute({"ask_folder": True}, context)
        context.pending_action = res1.pending_action

        turn2_output = self.dispatcher.process("never mind", context=context)
        self.assertIsNone(context.pending_action)
        self.assertIn("Cancelled", turn2_output)

    def test_new_tool_workflow_clears_pending_action(self):
        """Verify starting a different tool workflow (e.g. SYSTEM_INFO) clears pending action."""
        context = ConversationContext(user_input="List files.")
        dir_skill = DirectoryListingSkill()

        res1 = dir_skill.execute({"ask_folder": True}, context)
        context.pending_action = res1.pending_action

        # Turn 2: User asks for CPU usage (SYSTEM_INFO intent)
        turn2_output = self.dispatcher.process("What's my CPU usage?", context=context)
        self.assertIsNone(context.pending_action)
        self.assertIsNotNone(context.skill_result)
        self.assertIn("CPU", context.skill_result.message)

    def test_pending_action_timeout(self):
        """Verify pending action expires if elapsed time exceeds settings.pending_action_timeout."""
        context = ConversationContext(user_input="List files.")
        dir_skill = DirectoryListingSkill()

        res1 = dir_skill.execute({"ask_folder": True, "path": ""}, context)
        self.assertIsNotNone(res1.pending_action)
        context.pending_action = res1.pending_action
        if context.pending_action:
            context.pending_action.timestamp = time.time() - (settings.pending_action_timeout + 10)

        # Turn 2: User sends 'Downloads' after timeout
        turn2_output = self.dispatcher.process("Downloads.", context=context)
        self.assertIsNone(context.pending_action)


if __name__ == "__main__":
    unittest.main()
