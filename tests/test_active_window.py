import os
import unittest
from unittest.mock import patch, MagicMock

from runtime.intent import IntentRouter
from infrastructure.os.linux import LinuxOSAdapter
from skills.active_window import ActiveWindowSkill
from infrastructure.os import os_adapter


def _cp(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Build a fake subprocess.CompletedProcess."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _which_only(*tools: str):
    """shutil.which side_effect: only the named tools 'exist'."""
    return lambda t: f"/usr/bin/{t}" if t in tools else None


class TestActiveWindowRouting(unittest.TestCase):
    """Keyword router must send desktop-context queries to ACTIVE_WINDOW."""

    def setUp(self):
        self.router = IntentRouter()

    def test_active_window_phrases(self):
        positives = [
            "what app am i using",
            "what app am i using right now",
            "which app am i in",
            "what's the active window",
            "show me the active window",
            "which window is focused",
            "what window am i looking at",
            "what app has focus",
            "what's in focus",
            "tell me the foreground app",
        ]
        for phrase in positives:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    self.router.classify(phrase).intent_name,
                    "ACTIVE_WINDOW",
                )

    def test_near_misses_do_not_hijack(self):
        cases = {
            "list files in Downloads": "DIRECTORY_LISTING",
            "open firefox": "OPEN_FILE",
            "take a screenshot": "SCREENSHOT",
            "what time is it": "TIME_DATE",
            "watch this folder": "FILE_WATCH",
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, expected)

    def test_window_noun_alone_is_not_enough(self):
        # A bare 'window' mention without an active/focus context must not route here.
        res = self.router.classify("how do I resize a window in gnome")
        self.assertNotEqual(res.intent_name, "ACTIVE_WINDOW")


class TestLinuxActiveWindowBackends(unittest.TestCase):
    """Backend-chain behavior of LinuxOSAdapter.get_active_window."""

    def setUp(self):
        self.adapter = LinuxOSAdapter()

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("xdotool"))
    @patch("infrastructure.os.linux.subprocess.run")
    def test_xdotool_success(self, mock_run, _which):
        mock_run.side_effect = [
            _cp(stdout="Terminal — user@host\n"),
            _cp(stdout="1234\n"),
        ]
        with patch("psutil.Process") as mock_proc:
            mock_proc.return_value.name.return_value = "gnome-terminal-server"
            info = self.adapter.get_active_window()
        self.assertEqual(info["title"], "Terminal — user@host")
        self.assertEqual(info["app"], "gnome-terminal-server")
        self.assertEqual(info["source"], "xdotool")

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("xprop", "wmctrl"))
    @patch("infrastructure.os.linux.subprocess.run")
    def test_xprop_wmctrl_fallback(self, mock_run, _which):
        mock_run.side_effect = [
            _cp(stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x03A00007\n"),
            _cp(stdout="0x03a00007  0 myhost Mozilla Firefox\n0x01200003  0 myhost Terminal\n"),
        ]
        info = self.adapter.get_active_window()
        self.assertEqual(info["title"], "Mozilla Firefox")
        self.assertEqual(info["source"], "wmctrl")

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("gdbus"))
    @patch("infrastructure.os.linux.subprocess.run")
    def test_gnome_shell_eval_success(self, mock_run, _which):
        mock_run.return_value = _cp(
            stdout='(true, \'{"title": "index.ts — nexa", "app": "Code"}\')\n'
        )
        info = self.adapter.get_active_window()
        self.assertEqual(info["title"], "index.ts — nexa")
        self.assertEqual(info["app"], "Code")
        self.assertEqual(info["source"], "gnome-shell")

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("gdbus"))
    @patch("infrastructure.os.linux.subprocess.run")
    def test_nexa_extension_backend_success(self, mock_run, _which):
        # GVariant text format escapes an embedded apostrophe as \'
        mock_run.return_value = _cp(
            stdout='(\'{"title": "What\\\'s New", "app": "gnome-text-editor"}\',)\n'
        )
        info = self.adapter.get_active_window()
        self.assertEqual(info["title"], "What's New")
        self.assertEqual(info["app"], "gnome-text-editor")
        self.assertEqual(info["source"], "nexa-extension")

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("gdbus"))
    @patch("infrastructure.os.linux.subprocess.run")
    def test_extension_absent_falls_through_to_eval(self, mock_run, _which):
        mock_run.side_effect = [
            _cp(returncode=1, stderr="Error: org.freedesktop.DBus.Error.ServiceUnknown"),
            _cp(stdout='(true, \'{"title": "x", "app": "y"}\')\n'),
        ]
        info = self.adapter.get_active_window()
        self.assertEqual(info["source"], "gnome-shell")
        self.assertEqual(info["title"], "x")

    @patch("infrastructure.os.linux.shutil.which", return_value=None)
    def test_wayland_error_with_hint(self, _which):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            info = self.adapter.get_active_window()
        self.assertIn("error", info)
        self.assertIn("Wayland", info.get("hint", ""))

    @patch("infrastructure.os.linux.shutil.which", side_effect=_which_only("xdotool"))
    @patch("infrastructure.os.linux.subprocess.run", side_effect=[
        _cp(returncode=1, stderr="XGetWindowProperty failed"),
        _cp(returncode=1, stderr="XGetWindowProperty failed"),
    ])
    def test_xdotool_failure_degrades_to_error(self, _run, _which):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            info = self.adapter.get_active_window()
        self.assertIn("error", info)
        self.assertNotIn("title", info)


class TestActiveWindowSkill(unittest.TestCase):
    """Skill message formatting and failure handling."""

    def setUp(self):
        self.skill = ActiveWindowSkill()

    def test_success_with_app_and_title(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "Firefox", "title": "nexa – GitHub", "source": "mock"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertIn("Firefox", res.message)
        self.assertIn("nexa – GitHub", res.message)
        self.assertFalse(res.use_llm)

    def test_title_already_contains_app(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "Code", "title": "Code — main.py", "source": "mock"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        # App name should not be duplicated when already in the title
        self.assertEqual(res.message.count("Code"), 1)

    def test_vscode_style_title_parsed_naturally(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "code", "title": "README.md - nexa - Visual Studio Code",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertEqual(res.message,
                         "Looks like you're reading README.md in Visual Studio Code (nexa).")

    def test_bare_workspace_title_read_naturally(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "code", "title": "nexa - Visual Studio Code",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertEqual(res.message, "You're in Visual Studio Code, in the nexa workspace.")

    def test_friendly_alias_for_unknown_parsed_title(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "gnome-terminal-server",
                                        "title": "shikhar@shikhar-ubuntu: ~/Desktop/nexa",
                                        "source": "nexa-extension"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.message.startswith("You're in Terminal — "))

    def test_no_machine_literals_in_messages(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "org.gnome.Nautilus", "title": "", "source": "mock"}):
            res = self.skill.execute({}, None)
        self.assertIn("Files", res.message)
        self.assertNotIn("org.gnome", res.message)
        self.assertNotIn("Active window:", res.message)

    def test_messages_read_naturally(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"app": "Slack", "title": "#general — Workspace", "source": "mock"}):
            res = self.skill.execute({}, None)
        self.assertTrue(res.message.startswith("You're in Slack"))
        self.assertNotIn("Active window:", res.message)

    def test_error_includes_hint(self):
        with patch.object(os_adapter, "get_active_window",
                          return_value={"error": "Could not determine the active window",
                                        "hint": "sudo apt install xdotool"}):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertIn("xdotool", res.message)

    def test_not_implemented(self):
        with patch.object(os_adapter, "get_active_window", side_effect=NotImplementedError):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertIn("not supported", res.message.lower())


if __name__ == "__main__":
    unittest.main()
