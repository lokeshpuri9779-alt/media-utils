import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mpt_adapter import build_local_command, installed


class MoneyPrinterTurboAdapterTests(unittest.TestCase):
    def test_install_detection_is_fail_closed(self):
        with TemporaryDirectory() as tmp:
            self.assertFalse(installed(Path(tmp)))

    def test_command_requires_installed_engine(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                build_local_command(script="hello world", materials=["a.mp4"], root=Path(tmp))


if __name__ == "__main__":
    unittest.main()
