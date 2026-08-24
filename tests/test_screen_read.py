"""Phase 4b: screen reading (OCR fast path + optional vision model).

All backend seams (capture, OCR availability/extraction, vision
availability/description) are mocked — tests never touch the real screen,
tesseract, or Ollama.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from runtime.intent import IntentRouter
from skills import screen_read
from skills.screen_read import ScreenReadSkill


class TestScreenReadRouting(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def test_screen_read_phrases(self):
        positives = [
            "what's on my screen",
            "what is on my screen",
            "what's on screen",
            "read my screen",
            "read the screen",
            "what does my screen say",
            "what's written on my screen",
            "extract text from my screen",
            "text on my screen",
            "ocr my screen",
            "what error is on my screen",
        ]
        for phrase in positives:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, "SCREEN_READ")

    def test_query_extraction(self):
        res = self.router.classify("read my screen and tell me if the build failed")
        self.assertEqual(res.intent_name, "SCREEN_READ")
        self.assertEqual(res.args["query"], "and tell me if the build failed")

        bare = self.router.classify("what's on my screen?")
        self.assertEqual(bare.args["query"], "")

    def test_describe_phrases_set_the_describe_flag(self):
        for phrase in ("describe my screen", "describe what's on my screen", "what do you see on my screen"):
            with self.subTest(phrase=phrase):
                res = self.router.classify(phrase)
                self.assertEqual(res.intent_name, "SCREEN_READ")
                self.assertTrue(res.args["describe"])

    def test_plain_screen_read_phrases_do_not_describe(self):
        for phrase in ("what's on my screen", "read my screen", "read my screen and tell me if the build failed"):
            with self.subTest(phrase=phrase):
                self.assertFalse(self.router.classify(phrase).args["describe"])

    def test_tier_separation(self):
        cases = {
            "take a screenshot": "SCREENSHOT",
            "what app am i using": "ACTIVE_WINDOW",
            "what am i looking at": "WORK_CONTEXT",
            "what is this project": "REPO_INDEX",
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(self.router.classify(phrase).intent_name, expected)


class TestScreenReadSkill(unittest.TestCase):
    def setUp(self):
        self.skill = ScreenReadSkill()

    def test_ocr_path_grounds_extracted_text(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value="FAILED tests/test_x.py"):
            res = self.skill.execute({"query": ""}, None)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)
        self.assertTrue(res.allow_interpretation)
        self.assertIn("FAILED tests/test_x.py", res.data["Extracted screen text"])

    def test_ocr_long_text_is_truncated(self):
        long_text = "x" * 5000
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value=long_text):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertLessEqual(len(res.data["Extracted screen text"]), 4100)
        self.assertIn("truncated", res.data["Extracted screen text"])

    def test_ocr_empty_escalates_to_vision(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value=""), \
             patch.object(screen_read, "vision_available", return_value=True), \
             patch.object(screen_read, "describe_screen",
                          return_value="a desktop with a terminal and an editor open") as desc:
            res = self.skill.execute({"query": "is anything running?"}, None)
        self.assertTrue(res.success)
        self.assertFalse(res.use_llm)  # vision answers are already natural language
        self.assertIn("terminal and an editor", res.message)
        desc.assert_called_once()
        self.assertEqual(desc.call_args[0][1], "is anything running?")

    def test_describe_flag_skips_ocr_entirely(self):
        """Live trigger: screen full of browser text, user asked for a
        DESCRIPTION — OCR must not get a turn at UI-chrome text."""
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value="Cc Agent Mode v 3% Agent Mode v") as ocr, \
             patch.object(screen_read, "vision_available", return_value=True), \
             patch.object(screen_read, "describe_screen", return_value="a chat application in a browser") as desc:
            res = self.skill.execute({"query": "", "describe": True}, None)
        self.assertTrue(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("chat application", res.message)
        ocr.assert_not_called()  # the whole point of the describe flag
        desc.assert_called_once()

    def test_describe_flag_without_vision_degrades_to_ocr(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value="build finished ok"), \
             patch.object(screen_read, "vision_available", return_value=False):
            res = self.skill.execute({"query": "describe my screen", "describe": True}, None)
        self.assertTrue(res.success)
        self.assertTrue(res.use_llm)  # grounded OCR stand-in, honestly labelled
        self.assertIn("build finished ok", res.data["Extracted screen text"])
        self.assertIn("Vision description unavailable", res.data)

    def test_ocr_empty_no_vision_states_it(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value=""), \
             patch.object(screen_read, "vision_available", return_value=False):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("readable text", res.message)

    def test_vision_fallback_when_no_ocr(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=False), \
             patch.object(screen_read, "vision_available", return_value=True), \
             patch.object(screen_read, "describe_screen", return_value="A settings dialog is open."):
            res = self.skill.execute({"query": "what dialog is open?"}, None)
        self.assertTrue(res.success)
        self.assertEqual(res.message, "A settings dialog is open.")
        self.assertEqual(res.data["backend"], "vision")

    def test_no_backends_gives_install_hints(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=False), \
             patch.object(screen_read, "vision_available", return_value=False):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("tesseract-ocr", res.message)
        self.assertIn("ollama pull", res.message)

    def test_capture_failure_is_deterministic(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(False, "portal said no")):
            res = self.skill.execute({}, None)
        self.assertFalse(res.success)
        self.assertFalse(res.use_llm)
        self.assertIn("portal said no", res.message)

    def test_temp_capture_is_cleaned_up(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", return_value="some text"), \
             patch.object(screen_read.shutil, "rmtree") as rm:
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)
        rm.assert_called_once()
        self.assertIn("nexa-screen-", rm.call_args[0][0])

    def test_ocr_crash_falls_to_vision_or_empty_path(self):
        with patch.object(screen_read, "capture_screen_image", return_value=(True, "")), \
             patch.object(screen_read, "ocr_available", return_value=True), \
             patch.object(screen_read, "extract_text", side_effect=RuntimeError("tesseract exploded")), \
             patch.object(screen_read, "vision_available", return_value=False):
            res = self.skill.execute({}, None)
        self.assertTrue(res.success)  # graceful: empty-text path, not an exception
        self.assertFalse(res.use_llm)


class TestVisionImagePreparation(unittest.TestCase):
    """Live-observed failure: moondream answered the degenerate token
    "urn:1.0.0.0" to a full-resolution RGBA portal capture. describe_screen
    must normalize (RGB + downscale) before hitting the vision model."""

    def test_large_rgba_capture_is_downscaled_and_converted(self):
        from PIL import Image
        src = os.path.join(tempfile.mkdtemp(), "screen.png")
        Image.new("RGBA", (2000, 1200), (1, 2, 3, 255)).save(src)
        out = screen_read._prepare_image_for_vision(src)
        self.assertNotEqual(out, src)
        with Image.open(out) as im:
            self.assertEqual(im.mode, "RGB")
            self.assertEqual(im.size[0], 1280)
            self.assertLessEqual(im.size[1], 1280)

    def test_small_rgb_image_passes_through(self):
        from PIL import Image
        src = os.path.join(tempfile.mkdtemp(), "small.png")
        Image.new("RGB", (800, 600), (7, 7, 7)).save(src)
        self.assertEqual(screen_read._prepare_image_for_vision(src), src)

    def test_unreadable_image_falls_back_to_original(self):
        out = screen_read._prepare_image_for_vision("/nonexistent/screen.png")
        self.assertEqual(out, "/nonexistent/screen.png")

    def test_describe_screen_sends_the_prepared_image(self):
        with patch.object(screen_read, "_prepare_image_for_vision", return_value="/tmp/prepared.jpg") as prep, \
             patch.object(screen_read.ollama, "chat", return_value={"message": {"content": "blue"}}) as chat:
            ans = screen_read.describe_screen("/tmp/raw.png", "q")
        self.assertEqual(ans, "blue")
        prep.assert_called_once_with("/tmp/raw.png")
        self.assertEqual(chat.call_args.kwargs["messages"][0]["images"], ["/tmp/prepared.jpg"])


if __name__ == "__main__":
    unittest.main()
