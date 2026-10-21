import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from astra_v2.github_reserved_archive import ReservedReleaseArchive


class ReservedReleaseArchiveTests(unittest.TestCase):
    def test_rejects_invalid_package_before_reservation(self):
        ledger = Mock()
        bridge = ReservedReleaseArchive(Mock(), ledger)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                bridge.put(folder)
        ledger.transaction.assert_not_called()

    def test_reserves_before_archive_and_settles_after(self):
        calls = []
        ledger = Mock()
        ledger.transaction.side_effect = lambda fn: calls.append("ledger")
        bridge = ReservedReleaseArchive(Mock(), ledger)
        bridge.archive.put = Mock(side_effect=lambda *a, **k: calls.append("archive") or {"ok": True})
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "video.mp4").write_bytes(b"video")
            self.assertEqual(bridge.put(folder), {"ok": True})
        self.assertEqual(calls, ["ledger", "archive", "ledger"])

    def test_failed_upload_keeps_reservation(self):
        calls = []
        ledger = Mock()
        ledger.transaction.side_effect = lambda fn: calls.append("ledger")
        bridge = ReservedReleaseArchive(Mock(), ledger)
        bridge.archive.put = Mock(side_effect=RuntimeError("remote_error"))
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "video.mp4").write_bytes(b"video")
            with self.assertRaises(RuntimeError):
                bridge.put(folder)
        self.assertEqual(calls, ["ledger"])


if __name__ == "__main__":
    unittest.main()
