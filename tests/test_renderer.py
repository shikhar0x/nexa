import unittest
import io
from unittest.mock import patch
from runtime.renderer import ConsoleRenderer


class TestConsoleRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = ConsoleRenderer()

    def test_render_static(self):
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            result = self.renderer.render_static("Battery is 80%")
            self.assertEqual(result, "Battery is 80%")
            self.assertIn("Nexa: Battery is 80%\n", captured_output.getvalue())

    def test_render_stream_chunks(self):
        def sample_generator():
            yield "Your "
            yield "battery "
            yield "is "
            yield "at 84%."

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            accumulated = self.renderer.render_stream(sample_generator())
            self.assertEqual(accumulated, "Your battery is at 84%.")
            output_text = captured_output.getvalue()
            self.assertIn("Nexa: Your battery is at 84%.", output_text)


if __name__ == "__main__":
    unittest.main()
