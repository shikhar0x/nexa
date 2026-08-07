import unittest
from unittest.mock import patch, MagicMock

from runtime.context import ConversationContext
from skills.brightness import BrightnessSkill
from skills.volume import VolumeSkill
from skills.wifi import WifiSkill
from skills.power import PowerSkill
from skills.base import SkillResult


class TestSystemControlSkills(unittest.TestCase):
    def setUp(self):
        self.context = ConversationContext(user_input="test")

    # ── Brightness Skill Tests ───────────────────────────────────

    @patch("skills.brightness.os_adapter.get_brightness", return_value={"percent": 75, "raw_output": "75%"})
    def test_brightness_get_unconfirmed(self, mock_get):
        skill = BrightnessSkill()
        result = skill.execute({"action": "get"}, self.context)
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("75%", result.message)

    @patch("skills.brightness.os_adapter.set_brightness", return_value={"percent": 80, "status": "set"})
    @patch("skills.brightness.confirm_action", return_value=True)
    def test_brightness_set_confirmed(self, mock_confirm, mock_set):
        skill = BrightnessSkill()
        result = skill.execute({"action": "set", "level": 80}, self.context)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("80%", result.message)
        mock_confirm.assert_called_once_with("set screen brightness to 80%")

    @patch("skills.brightness.confirm_action", return_value=False)
    def test_brightness_set_cancelled(self, mock_confirm):
        skill = BrightnessSkill()
        result = skill.execute({"action": "set", "level": 80}, self.context)
        self.assertFalse(result.success)
        self.assertEqual(result.data.get("status"), "cancelled")

    # ── Volume Skill Tests ───────────────────────────────────────

    @patch("skills.volume.os_adapter.get_volume", return_value={"percent": 50, "muted": False})
    def test_volume_get_unconfirmed(self, mock_get):
        skill = VolumeSkill()
        result = skill.execute({"action": "get"}, self.context)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("50%", result.message)

    @patch("skills.volume.os_adapter.set_volume", return_value={"percent": 70, "status": "set"})
    @patch("skills.volume.confirm_action", return_value=True)
    def test_volume_set_confirmed(self, mock_confirm, mock_set):
        skill = VolumeSkill()
        result = skill.execute({"action": "set", "level": 70}, self.context)
        self.assertTrue(result.success)
        mock_confirm.assert_called_once_with("set system volume to 70%")

    @patch("skills.volume.os_adapter.set_mute", return_value={"muted": True, "status": "muted"})
    @patch("skills.volume.confirm_action", return_value=True)
    def test_volume_mute_confirmed(self, mock_confirm, mock_mute):
        skill = VolumeSkill()
        result = skill.execute({"action": "mute"}, self.context)
        self.assertTrue(result.success)
        mock_confirm.assert_called_once_with("mute system audio")

    # ── Wi-Fi Skill Tests ────────────────────────────────────────

    @patch("skills.wifi.os_adapter.get_wifi_status", return_value={"connected": True, "ssid": "HomeWiFi", "signal": "90", "security": "WPA2"})
    def test_wifi_status_unconfirmed(self, mock_status):
        skill = WifiSkill()
        result = skill.execute({"action": "status"}, self.context)
        self.assertTrue(result.success)
        self.assertIn("HomeWiFi", result.message)

    @patch("skills.wifi.os_adapter.list_wifi_networks", return_value=[{"ssid": "Net1", "signal": "80", "security": "WPA2"}])
    def test_wifi_list_unconfirmed(self, mock_list):
        skill = WifiSkill()
        result = skill.execute({"action": "list"}, self.context)
        self.assertTrue(result.success)
        self.assertIn("Net1", result.message)

    @patch("skills.wifi.os_adapter.toggle_wifi", return_value={"wifi_enabled": False, "status": "off"})
    @patch("skills.wifi.confirm_action", return_value=True)
    def test_wifi_off_confirmed(self, mock_confirm, mock_toggle):
        skill = WifiSkill()
        result = skill.execute({"action": "off"}, self.context)
        self.assertTrue(result.success)
        mock_confirm.assert_called_once_with("turn off Wi-Fi")

    @patch("skills.wifi.confirm_action", return_value=False)
    def test_wifi_on_cancelled(self, mock_confirm):
        skill = WifiSkill()
        result = skill.execute({"action": "on"}, self.context)
        self.assertFalse(result.success)
        self.assertEqual(result.data.get("status"), "cancelled")

    # ── Power Skill Tests ────────────────────────────────────────

    @patch("skills.power.os_adapter.power_action", return_value={"action": "shutdown", "delay_minutes": 1, "status": "scheduled"})
    @patch("skills.power.confirm_action", return_value=True)
    def test_power_shutdown_confirmed(self, mock_confirm, mock_power):
        skill = PowerSkill()
        result = skill.execute({"action": "shutdown", "delay": 60}, self.context)
        self.assertTrue(result.success)
        self.assertFalse(result.use_llm)
        self.assertIn("shutdown scheduled", result.message.lower())

    @patch("skills.power.os_adapter.power_action", return_value={"action": "restart", "delay_minutes": 1, "status": "scheduled"})
    @patch("skills.power.confirm_action", return_value=True)
    def test_power_restart_confirmed(self, mock_confirm, mock_power):
        skill = PowerSkill()
        result = skill.execute({"action": "restart", "delay": 60}, self.context)
        self.assertTrue(result.success)
        self.assertIn("restart scheduled", result.message.lower())

    @patch("skills.power.confirm_action", return_value=False)
    def test_power_shutdown_cancelled(self, mock_confirm):
        skill = PowerSkill()
        result = skill.execute({"action": "shutdown", "delay": 60}, self.context)
        self.assertFalse(result.success)
        self.assertEqual(result.data.get("status"), "cancelled")


if __name__ == "__main__":
    unittest.main()
