import os
import tempfile
import time
import unittest
from unittest.mock import patch

from runtime.intent import IntentRouter
from skills.registry import SkillRegistry
from skills.resolver import CapabilityResolver
from skills.file_watch import FileWatchSkill
from infrastructure import file_watcher


def _reset_watches():
    for w in list(file_watcher._active.values()):
        w.stop()
    file_watcher._active.clear()


class TestFileWatchIntent(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_watch_this_folder(self):
        res = self.router.classify("watch this folder")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual(res.args.get("action"), "start")
        self.assertEqual(res.args.get("path"), "")

    def test_keep_an_eye_on_this_repo(self):
        res = self.router.classify("keep an eye on this repo")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual(res.args.get("action"), "start")

    def test_notify_me_when_files_change(self):
        res = self.router.classify("notify me when files change in /tmp/demo")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual(res.args.get("action"), "start")
        self.assertEqual(res.args.get("path"), "/tmp/demo")

    def test_stop_watching(self):
        res = self.router.classify("stop watching")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual(res.args.get("action"), "stop")

    def test_stop_watching_path(self):
        res = self.router.classify("stop watching /tmp/demo")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual((res.args.get("action"), res.args.get("path")), ("stop", "/tmp/demo"))

    def test_watch_status(self):
        res = self.router.classify("what are you watching")
        self.assertEqual(res.intent_name, "FILE_WATCH")
        self.assertEqual(res.args.get("action"), "status")

    def test_collisions_untouched(self):
        self.assertEqual(
            self.router.classify("what's in my downloads").intent_name, "DIRECTORY_LISTING"
        )
        self.assertEqual(
            self.router.classify("index this repo").intent_name, "REPO_INDEX"
        )


class TestFileWatchSkill(unittest.TestCase):
    """Action plumbing with threads disabled (DirWatch.start no-op'd)."""

    def setUp(self):
        _reset_watches()
        self.tmp = tempfile.TemporaryDirectory()
        self.skill = FileWatchSkill()
        self._start_patch = patch("infrastructure.file_watcher.DirWatch.start", lambda self: None)
        self._start_patch.start()

    def tearDown(self):
        self._start_patch.stop()
        _reset_watches()
        self.tmp.cleanup()

    def test_start_status_stop_cycle(self):
        res = self.skill.execute({"action": "start", "path": self.tmp.name}, context=None)
        self.assertTrue(res.success)
        self.assertIn("Watching", res.message)

        res = self.skill.execute({"action": "status"}, context=None)
        self.assertTrue(res.success)
        self.assertIn(self.tmp.name, res.message)

        res = self.skill.execute({"action": "stop", "path": self.tmp.name}, context=None)
        self.assertTrue(res.success)
        self.assertIn("Stopped", res.message)

        res = self.skill.execute({"action": "status"}, context=None)
        self.assertIn("Not watching anything", res.message)

    def test_duplicate_start(self):
        self.skill.execute({"action": "start", "path": self.tmp.name}, context=None)
        res = self.skill.execute({"action": "start", "path": self.tmp.name}, context=None)
        self.assertFalse(res.success)
        self.assertIn("Already watching", res.message)

    def test_start_missing_path(self):
        res = self.skill.execute({"action": "start", "path": "/definitely/not/here"}, context=None)
        self.assertFalse(res.success)
        self.assertIn("Could not find", res.message)

    def test_start_file_rejected(self):
        fp = os.path.join(self.tmp.name, "f.txt")
        open(fp, "w").write("x")
        res = self.skill.execute({"action": "start", "path": fp}, context=None)
        self.assertFalse(res.success)
        self.assertIn("not a directory", res.message)

    def test_stop_with_no_active_watches(self):
        res = self.skill.execute({"action": "stop"}, context=None)
        self.assertFalse(res.success)
        self.assertIn("No active watches", res.message)


class TestFileWatchIntegration(unittest.TestCase):
    """Real watchfiles watch on a temp dir; notification path verified."""

    def setUp(self):
        _reset_watches()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        file_watcher.stop_all_watches()
        _reset_watches()
        self.tmp.cleanup()

    def test_change_fires_notification(self):
        try:
            import watchfiles  # noqa: F401
        except ImportError:
            self.skipTest("watchfiles not installed")

        with patch("infrastructure.file_watcher.send_notification") as mock_notify:
            ok, msg = file_watcher.start_watch(self.tmp.name)
            self.assertTrue(ok, msg)

            deadline = time.time() + 10
            while time.time() < deadline:
                with open(os.path.join(self.tmp.name, "hello.txt"), "w") as f:
                    f.write(str(time.time()))
                if mock_notify.called:
                    break
                time.sleep(0.3)

            self.assertTrue(mock_notify.called, "no desktop notification fired within 10s")
            body = mock_notify.call_args[0][1]
            self.assertIn("hello.txt", body)


class TestFileWatchWiring(unittest.TestCase):
    def test_dispatcher_registers_file_watch(self):
        from runtime.dispatcher import Dispatcher
        d = Dispatcher()
        d.initialize()
        self.assertIsInstance(d.registry.get("FILE_WATCH"), FileWatchSkill)

    def test_no_general_fanout_hijack(self):
        registry = SkillRegistry()
        registry.register(FileWatchSkill())
        resolver = CapabilityResolver(registry=registry)
        self.assertEqual(
            resolver.resolve("GENERAL", "would you watch my back while i deploy"),
            [],
        )

    # NOTE: deliberately no prompts.json e2e fixture for FILE_WATCH — the
    # regression runner executes the real dispatcher, and starting a watch
    # would fire desktop notifications during test runs.


if __name__ == "__main__":
    unittest.main()
