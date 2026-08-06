import unittest
from unittest.mock import patch
from infrastructure.os.base import BaseOSAdapter
from infrastructure.os.linux import LinuxOSAdapter
from infrastructure.os.factory import get_os_adapter


class TestOSAdapter(unittest.TestCase):
    def test_factory_returns_adapter(self):
        adapter = get_os_adapter()
        self.assertIsInstance(adapter, BaseOSAdapter)

    def test_linux_adapter_methods(self):
        adapter = LinuxOSAdapter()
        self.assertEqual(adapter.get_system_drive(), "/")

    def test_linux_run_command(self):
        adapter = LinuxOSAdapter()
        res = adapter.run_command(["echo", "hello"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("hello", res.stdout)

    @patch("sys.platform", "win32")
    def test_unsupported_platform_raises_error(self):
        with self.assertRaises(NotImplementedError):
            get_os_adapter()


if __name__ == "__main__":
    unittest.main()
