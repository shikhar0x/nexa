import os
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from runtime.intent import IntentRouter
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.git import GitSkill


class TestGitAddIntent(unittest.TestCase):
    """Keyword router classification for the GIT_ADD (stage-only) intent."""

    def setUp(self):
        self.router = IntentRouter()

    def test_add_these_files_to_git(self):
        res = self.router.classify("add these files to git")
        self.assertEqual(res.intent_name, "GIT_ADD")
        self.assertEqual(res.args.get("paths"), [])  # no path tokens -> stage all

    def test_git_add_with_explicit_path(self):
        res = self.router.classify("git add skills/repo_index.py")
        self.assertEqual(res.intent_name, "GIT_ADD")
        self.assertEqual(res.args.get("paths"), ["skills/repo_index.py"])

    def test_stage_my_changes(self):
        self.assertEqual(self.router.classify("stage my changes").intent_name, "GIT_ADD")

    def test_add_and_commit_still_wins(self):
        # "git add and commit" contains "git add" — precedence must keep it
        # on GIT_ADD_COMMIT, never GIT_ADD.
        res = self.router.classify("git add and commit: wire up routing")
        self.assertEqual(res.intent_name, "GIT_ADD_COMMIT")
        self.assertTrue(res.args.get("message"))

    def test_read_intents_untouched(self):
        self.assertEqual(self.router.classify("git diff").intent_name, "GIT_DIFF")
        self.assertEqual(self.router.classify("git status").intent_name, "GIT_STATUS")


class TestGitAddSkill(unittest.TestCase):
    """GitSkill stage flow against a throwaway repo (never the real one)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self._git(["init"])
        self._git(["config", "user.email", "test@example.com"])
        self._git(["config", "user.name", "Test"])
        self._write("a.txt", "one")
        self._write("b.txt", "two")
        self._git(["add", "."])
        self._git(["commit", "-m", "init"])
        # Baseline: clean tree. Now dirty it + add an untracked file.
        self._write("a.txt", "changed")
        self._write("c.txt", "new")
        self.skill = GitSkill()
        self.ctx = types.SimpleNamespace(conversation_state={"intent": "GIT_ADD"})

    def _git(self, cmd):
        return subprocess.run(["git"] + cmd, cwd=self.root, check=True,
                              capture_output=True, text=True)

    def _write(self, name, content):
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            f.write(content)

    def _staged(self):
        res = self._git(["diff", "--cached", "--name-only"])
        return set(res.stdout.split())

    def tearDown(self):
        self.tmp.cleanup()

    def test_stage_explicit_file(self):
        with patch("skills.git.confirm_action", return_value=True):
            res = self.skill.execute({"repo": self.root, "paths": ["a.txt"]}, self.ctx)
        self.assertTrue(res.success)
        self.assertEqual(self._staged(), {"a.txt"})
        self.assertIn("a.txt", res.message)

    def test_stage_all_when_no_paths(self):
        with patch("skills.git.confirm_action", return_value=True):
            res = self.skill.execute({"repo": self.root, "paths": []}, self.ctx)
        self.assertTrue(res.success)
        self.assertEqual(self._staged(), {"a.txt", "c.txt"})

    def test_cancelled_stages_nothing(self):
        with patch("skills.git.confirm_action", return_value=False):
            res = self.skill.execute({"repo": self.root, "paths": ["a.txt"]}, self.ctx)
        self.assertFalse(res.success)
        self.assertIn("Cancelled", res.message)
        self.assertEqual(self._staged(), set())

    def test_bad_path_surfaces_git_error(self):
        with patch("skills.git.confirm_action", return_value=True):
            res = self.skill.execute({"repo": self.root, "paths": ["nope.txt"]}, self.ctx)
        self.assertFalse(res.success)
        self.assertIn("git add failed", res.message)


class TestGitAddWiring(unittest.TestCase):
    def test_dispatcher_alias_registered(self):
        from runtime.dispatcher import Dispatcher
        d = Dispatcher()
        d.initialize()
        self.assertIsInstance(d.registry.get("GIT_ADD"), GitSkill)

    def test_no_general_fanout_hijack(self):
        # Bare substrings like "git"/"commit" must not fan an unrelated intent
        # out to GitSkill (this is what mangled "add these files to git"
        # before the GIT_ADD intent existed).
        registry = SkillRegistry()
        registry.register(GitSkill())
        resolver = CapabilityResolver(registry=registry)
        self.assertEqual(
            resolver.resolve("GENERAL", "how do i undo a git commit from last week"),
            [],
        )

    # NOTE: deliberately no prompts.json e2e fixture for GIT_ADD — the
    # regression runner executes the real dispatcher, and staging files
    # during a test run would mutate the developer's actual git index.


if __name__ == "__main__":
    unittest.main()
