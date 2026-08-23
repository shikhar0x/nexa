import os
import tempfile
import unittest

from runtime.intent import IntentRouter
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.build_log import BuildLogSkill, MAX_LOG_CHARS


class TestBuildLogIntent(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_explain_this_error(self):
        self.assertEqual(
            self.router.classify("explain this error").intent_name, "BUILD_LOG"
        )

    def test_why_did_the_build_fail(self):
        self.assertEqual(
            self.router.classify("why did the build fail").intent_name, "BUILD_LOG"
        )

    def test_path_extraction(self):
        res = self.router.classify("explain the error in /tmp/build.log")
        self.assertEqual(res.intent_name, "BUILD_LOG")
        self.assertEqual(res.args.get("path"), "/tmp/build.log")


class TestBuildLogSkill(unittest.TestCase):
    def setUp(self):
        self.skill = BuildLogSkill()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_log(self, content: str, name: str = "build.log") -> str:
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reads_and_explains_log_file(self):
        path = self._write_log("make: *** [foo] Error 1\n")
        res = self.skill.execute({"path": path}, context=None)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)               # explanation goes through the LLM
        self.assertIn("Error 1", res.message)
        self.assertTrue(res.allow_interpretation)

    def test_missing_file_fails_cleanly(self):
        res = self.skill.execute({"path": "/definitely/not/here.log"}, context=None)
        self.assertFalse(res.success)
        self.assertIn("Could not find", res.message)
        self.assertFalse(res.use_llm)

    def test_empty_log_is_deterministic(self):
        path = self._write_log("   \n")
        res = self.skill.execute({"path": path}, context=None)
        self.assertTrue(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("No output/error found", res.message)

    def test_no_args_shows_usage(self):
        res = self.skill.execute({}, context=None)
        self.assertFalse(res.success)
        self.assertIn("No log file or command provided", res.message)

    def test_long_log_is_truncated(self):
        path = self._write_log("x" * (MAX_LOG_CHARS + 500))
        res = self.skill.execute({"path": path}, context=None)
        self.assertTrue(res.success)
        self.assertIn("Truncated", res.message)
        self.assertIn(str(MAX_LOG_CHARS + 500), res.message)

    def test_command_output_mode(self):
        res = self.skill.execute({"command": "echo boom >&2; exit 1"}, context=None)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)
        self.assertIn("boom", res.message)
        self.assertIn("exit 1", res.message)


class TestBuildLogRouting(unittest.TestCase):
    def test_no_general_fanout_hijack(self):
        # A conversational message containing "failed"/"test"/"log" must not
        # fan out to BuildLogSkill on bare substrings.
        registry = SkillRegistry()
        registry.register(BuildLogSkill())
        resolver = CapabilityResolver(registry=registry)
        self.assertEqual(
            resolver.resolve("GENERAL", "i failed my driving test today"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
