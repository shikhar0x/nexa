"""XDG portal capture correctness (live-observed failures, Phase 4b bring-up):

The portal Screenshot method is async: the call returns a Request token and
the result arrives later as a Response signal. One-shot callers (gdbus) exit
before the signal, the portal cancels the request, and NO file appears — the
flaky "sometimes a screenshot, sometimes not" behavior from live testing.
Nexa therefore captures through scripts/portal_screenshot.py: a tiny GLib
bridge (system python + gi) that blocks until the real Response.

These tests pin the bridge contract and the surrounding capture plumbing —
no real portal or gi needed.
"""

import unittest
from unittest.mock import patch

from skills import screenshot as shot


class TestPortalHelperRun(unittest.TestCase):
    def test_ok_line_yields_path(self):
        with patch.object(shot.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "OK /home/x/Pictures/Screenshots/Screenshot From now.png\n"
            run.return_value.stderr = ""
            ok, payload = shot._run_portal_helper()
        self.assertTrue(ok, payload)
        self.assertEqual(payload, "/home/x/Pictures/Screenshots/Screenshot From now.png")

    def test_err_line_yields_clean_message(self):
        with patch.object(shot.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = "ERR screenshot request was cancelled\n"
            run.return_value.stderr = ""
            ok, payload = shot._run_portal_helper()
        self.assertFalse(ok)
        self.assertEqual(payload, "screenshot request was cancelled")

    def test_hash_diagnostic_lines_are_ignored(self):
        with patch.object(shot.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "# python=3.13 gi=3.50\n# request-path=/x\nOK /tmp/shot.png\n"
            run.return_value.stderr = ""
            ok, payload = shot._run_portal_helper()
        self.assertTrue(ok, payload)
        self.assertEqual(payload, "/tmp/shot.png")

    def test_last_verdict_line_wins(self):
        with patch.object(shot.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = "OK /tmp/stale.png\nERR portal-call: type=X args=(0,)\n"
            run.return_value.stderr = ""
            ok, payload = shot._run_portal_helper()
        self.assertFalse(ok)
        self.assertEqual(payload, "portal-call: type=X args=(0,)")

    def test_forensic_err_detail_passes_through_verbatim(self):
        with patch.object(shot.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stdout = (
                "# screenshot-interface-version=2\n"
                "ERR wait: no portal Response signal within 20s\n"
            )
            run.return_value.stderr = ""
            ok, payload = shot._run_portal_helper()
        self.assertFalse(ok)
        self.assertEqual(payload, "wait: no portal Response signal within 20s")

    def test_helper_exception_is_an_error_not_a_crash(self):
        with patch.object(shot.subprocess, "run", side_effect=FileNotFoundError("no python")):
            ok, payload = shot._run_portal_helper()
        self.assertFalse(ok)
        self.assertIn("no python", payload)


class TestPortalMoveIntoPlace(unittest.TestCase):
    def test_produced_file_is_moved(self):
        with patch.object(shot, "_run_portal_helper", return_value=(True, "/tmp/portal.png")), \
             patch.object(shot.os.path, "exists", return_value=True), \
             patch.object(shot.shutil, "move") as mv:
            ok, err = shot._xdg_portal_screenshot("/tmp/nexa-screen-x/screen.png")
        self.assertTrue(ok, err)
        mv.assert_called_once_with("/tmp/portal.png", "/tmp/nexa-screen-x/screen.png")

    def test_missing_file_after_success_is_flagged(self):
        with patch.object(shot, "_run_portal_helper", return_value=(True, "/tmp/portal.png")), \
             patch.object(shot.os.path, "exists", return_value=False):
            ok, err = shot._xdg_portal_screenshot("/tmp/nexa-screen-x/screen.png")
        self.assertFalse(ok)
        self.assertIn("file is missing", err)

    def test_helper_error_passes_through(self):
        with patch.object(shot, "_run_portal_helper", return_value=(False, "python3-gi unavailable")):
            ok, err = shot._xdg_portal_screenshot("/tmp/nexa-screen-x/screen.png")
        self.assertFalse(ok)
        self.assertIn("python3-gi unavailable", err)


class TestCaptureChainPortalIntegration(unittest.TestCase):
    def test_portal_success_wins_the_chain(self):
        with patch.object(shot, "_find_screenshot_backends", return_value=["gnome_shell_dbus", "xdg_portal"]), \
             patch.object(shot, "_gnome_shell_screenshot", return_value=(False, "AccessDenied")), \
             patch.object(shot, "_xdg_portal_screenshot", return_value=(True, "")), \
             patch.object(shot.os.path, "exists", return_value=True):
            ok, err = shot.capture_screen_image("/tmp/x.png")
        self.assertTrue(ok, err)

    def test_all_backend_errors_are_accumulated(self):
        with patch.object(shot, "_find_screenshot_backends", return_value=["gnome_shell_dbus", "xdg_portal"]), \
             patch.object(shot, "_gnome_shell_screenshot", return_value=(False, "dbus said no")), \
             patch.object(shot, "_xdg_portal_screenshot", return_value=(False, "portal denied")), \
             patch.object(shot.os.path, "exists", return_value=False):
            ok, err = shot.capture_screen_image("/tmp/x.png")
        self.assertFalse(ok)
        self.assertIn("dbus said no", err)   # the first backend's error survived
        self.assertIn("portal denied", err)  # ... alongside the second one's


class TestHelperSelfReport(unittest.TestCase):
    """The bridge script's pure logic — importable without gi (gi loads lazily
    inside main()). Pins the forensic format that made the live KeyError(0)
    diagnosable."""

    @staticmethod
    def _load_helper_module():
        import importlib.util
        from pathlib import Path
        helper = Path(__file__).resolve().parents[1] / "scripts" / "portal_screenshot.py"
        spec = importlib.util.spec_from_file_location("portal_screenshot", helper)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_describe_error_plain_exception(self):
        mod = self._load_helper_module()
        desc = mod._describe_error(KeyError(0))
        self.assertIn("type=builtins.KeyError", desc)
        self.assertIn("args=(0,)", desc)
        self.assertIn("str=0", desc)

    def test_describe_error_glib_style_attributes(self):
        mod = self._load_helper_module()

        class FakeGLibError(Exception):
            domain = "g-dbus-error-quark"
            code = 30
            message = "Denied"

        desc = mod._describe_error(FakeGLibError("Denied"))
        self.assertIn("domain='g-dbus-error-quark'", desc)
        self.assertIn("code=30", desc)


if __name__ == "__main__":
    unittest.main()
