import json
import os
import tempfile
import unittest
from unittest.mock import patch

from runtime.intent import IntentRouter
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.repo_index import RepoIndexSkill


def _make_registry() -> SkillRegistry:
    """Registry wired the way Dispatcher._register_default_skills wires REPO_INDEX."""
    registry = SkillRegistry()
    registry.register(RepoIndexSkill())
    repo_skill = registry.get("REPO_INDEX")
    registry.register_alias("REPO_INDEX", repo_skill)
    return registry


class TestRepoIndexIntent(unittest.TestCase):
    """Keyword router classification for the REPO_INDEX intent."""

    def setUp(self):
        self.router = IntentRouter()

    def test_what_does_this_project_do(self):
        res = self.router.classify("what does this project do?")
        self.assertEqual(res.intent_name, "REPO_INDEX")
        self.assertEqual(res.args.get("path"), "")

    def test_index_this_repo(self):
        res = self.router.classify("index this repo")
        self.assertEqual(res.intent_name, "REPO_INDEX")

    def test_overview_and_structure_phrases(self):
        self.assertEqual(
            self.router.classify("give me a project overview").intent_name, "REPO_INDEX"
        )
        self.assertEqual(
            self.router.classify("show repo structure").intent_name, "REPO_INDEX"
        )
        self.assertEqual(
            self.router.classify("what's the tech stack?").intent_name, "REPO_INDEX"
        )

    def test_path_extraction(self):
        res = self.router.classify("explain this codebase in ~/projects/nexa")
        self.assertEqual(res.intent_name, "REPO_INDEX")
        self.assertEqual(res.args.get("path"), "~/projects/nexa")

        res2 = self.router.classify("summarize the project in /tmp/demo")
        self.assertEqual(res2.intent_name, "REPO_INDEX")
        self.assertEqual(res2.args.get("path"), "/tmp/demo")

    def test_git_and_build_log_not_hijacked(self):
        self.assertEqual(
            self.router.classify("is my repo clean?").intent_name, "GIT_STATUS"
        )
        self.assertEqual(
            self.router.classify("what branch am I on").intent_name, "GIT_STATUS"
        )
        self.assertEqual(
            self.router.classify("explain this error").intent_name, "BUILD_LOG"
        )

    def test_extract_args_for_hybrid_path(self):
        self.assertEqual(
            self.router.extract_args("REPO_INDEX", "Summarize this project in /tmp/demo"),
            {"path": "/tmp/demo"},
        )
        self.assertEqual(
            self.router.extract_args("REPO_INDEX", "what does this project do?"),
            {"path": ""},
        )


class TestRepoIndexRouting(unittest.TestCase):
    """LLM-fallback routing + capability resolution for REPO_INDEX."""

    def test_in_llm_classifiable_whitelist(self):
        from config.constants import LLM_CLASSIFIABLE_INTENTS
        self.assertIn("REPO_INDEX", LLM_CLASSIFIABLE_INTENTS)

    def test_hybrid_llm_fallback_routes_repo_index(self):
        from runtime.intent_hybrid import HybridIntentClassifier

        classifier = HybridIntentClassifier()
        fake = {"message": {"content": json.dumps({"intent": "REPO_INDEX"})}}
        with patch("ollama.chat", return_value=fake):
            res = classifier.classify("can you walk me through what this codebase is about?")
        self.assertEqual(res.intent_name, "REPO_INDEX")
        self.assertIn("path", res.args)

    def test_resolver_direct_alias(self):
        registry = _make_registry()
        resolver = CapabilityResolver(registry=registry)
        matched = resolver.resolve("REPO_INDEX", "what does this project do?")
        self.assertEqual([s.name for s in matched], ["REPO_INDEX"])

    def test_resolver_does_not_hijack_unmatched_intents(self):
        # Unmatched intents must not fan out to RepoIndexSkill just because
        # the user input happens to contain the word "project" or "repo".
        registry = _make_registry()
        resolver = CapabilityResolver(registry=registry)
        matched = resolver.resolve("MEMORY_DATE", "what did we do on the project monday")
        self.assertEqual(matched, [])


class TestRepoIndexSkill(unittest.TestCase):
    """RepoIndexSkill behavior against a synthetic project tree."""

    def setUp(self):
        self.skill = RepoIndexSkill()
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Demo Project\n\nA demo project for testing.\n")
        with open(os.path.join(root, "main.py"), "w", encoding="utf-8") as f:
            f.write("print('hello')\n")
        # pyproject.toml must NOT outrank main.py as the entry point
        with open(os.path.join(root, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'demo'\n")
        os.mkdir(os.path.join(root, "pkg"))
        with open(os.path.join(root, "pkg", "mod.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        os.mkdir(os.path.join(root, "node_modules"))
        with open(os.path.join(root, "node_modules", "junk.js"), "w", encoding="utf-8") as f:
            f.write("junk\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_summarizes_repo_with_readme(self):
        result = self.skill.execute({"path": self.tmp.name}, context=None)
        self.assertTrue(result.success)
        self.assertIn("main.py", result.message)          # entry point detected
        self.assertIn("README", result.message)
        self.assertIn("Demo Project", result.message)     # README content included
        self.assertTrue(result.use_llm)                   # LLM summarizes README
        self.assertNotIn("junk.js", result.message)       # heavy dirs skipped
        self.assertNotIn("node_modules", result.message)

    def test_no_readme_stays_deterministic(self):
        os.remove(os.path.join(self.tmp.name, "README.md"))
        result = self.skill.execute({"path": self.tmp.name}, context=None)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("No README found", result.message)

    def test_missing_path_fails(self):
        result = self.skill.execute({"path": "/definitely/not/here"}, context=None)
        self.assertFalse(result.success)

    def test_empty_dir(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.mkdir(empty)
        result = self.skill.execute({"path": empty}, context=None)
        self.assertTrue(result.success)
        self.assertIn("empty", result.message.lower())
        self.assertFalse(result.use_llm)

    def test_file_path_rejected(self):
        result = self.skill.execute(
            {"path": os.path.join(self.tmp.name, "main.py")}, context=None
        )
        self.assertFalse(result.success)
        self.assertIn("not a directory", result.message)


if __name__ == "__main__":
    unittest.main()
