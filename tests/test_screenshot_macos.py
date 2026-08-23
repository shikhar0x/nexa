"""macOS screenshot backend regression coverage.

The user's tree carries a hand-written macOS `screencapture` expectation in
tests/test_skills.py that the sandbox copy never had — the Phase 4b capture
refactor dropped the native macOS path without any sandbox test noticing.
These tests pin it on both sides: the skill-level result (data["tool"]) and
the shared capture chain.
"""

import unittest
from unittest.mock import patch

from skills.base import SkillResult
from skills.screenshot import ScreenshotSkill, capture_screen_image


class TestScreenshotMacOS(unittest.TestCase):
    def test_screenshot_skill_macos(self):
        # Mirrors the user's pre-existing expectation in tests/test_skills.py.
        with patch("skills.screenshot.confirm_action", return_value=True), \
             patch("skills.screenshot.subprocess.run") as mock_run, \
             patch("skills.screenshot.os.path.exists", return_value=True), \
             patch("skills.screenshot.os.makedirs"), \
             patch("skills.screenshot.shutil.which", return_value="/usr/bin/screencapture"), \
             patch("sys.platform", "darwin"):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            result = ScreenshotSkill().execute({}, None)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("tool"), "screencapture")

    def test_capture_chain_prefers_screencapture_on_darwin(self):
        # ScreenRead rides on capture_screen_image — macOS must use the native tool.
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd[0])

            class R:
                returncode = 0
                stderr = ""
            return R()

        with patch("skills.screenshot.subprocess.run", side_effect=fake_run), \
             patch("skills.screenshot.os.path.exists", return_value=True), \
             patch("skills.screenshot.shutil.which",
                   side_effect=lambda name: "/usr/bin/screencapture" if name == "screencapture" else None), \
             patch("sys.platform", "darwin"):
            ok, err = capture_screen_image("/tmp/nexa-fake-capture.png")
        self.assertTrue(ok, err)
        self.assertEqual(calls, ["screencapture"])

    def test_linux_chain_unaffected(self):
        # No screencapture on Linux; gdbus-based Wayland backends lead.
        with patch("skills.screenshot.shutil.which",
                   side_effect=lambda name: "/usr/bin/gdbus" if name == "gdbus" else None):
            from skills.screenshot import _find_screenshot_backends
            backends = _find_screenshot_backends()
        self.assertNotIn("screencapture", backends)
        self.assertEqual(backends[0], "gnome_shell_dbus")


if __name__ == "__main__":
    unittest.main()
