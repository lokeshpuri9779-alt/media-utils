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


    def test_duplicate_active_reservation_fails_before_upload(self):
        from astra_v2.github_storage_ledger import SCHEMA
        state = {"schema": SCHEMA, "capacity_bytes": 1000000,
                 "used_bytes": 0, "reservations": {}}
        ledger = Mock()
        def transaction(transform):
            nonlocal state
            state = transform(state)
        ledger.transaction.side_effect = transaction
        bridge = ReservedReleaseArchive(Mock(), ledger)
        def fail_upload(*args, **kwargs):
            raise RuntimeError("interrupted_upload")
        bridge.archive.put = Mock(side_effect=fail_upload)
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "video.mp4").write_bytes(b"video")
            with self.assertRaisesRegex(RuntimeError, "interrupted_upload"):
                bridge.put(folder)
            with self.assertRaisesRegex(RuntimeError, "reservation_already_active"):
                bridge.put(folder)
        bridge.archive.put.assert_called_once()

    def test_same_content_same_reservation_across_paths(self):
        from astra_v2.github_storage_ledger import SCHEMA
        identities = []
        state = {"schema": SCHEMA, "capacity_bytes": 1000000,
                 "used_bytes": 0, "reservations": {}}
        def record(transform):
            nonlocal state
            result = transform(state)
            state = result
            if result["reservations"]:
                identities.extend(result["reservations"].keys())
        ledger = Mock()
        ledger.transaction.side_effect = record
        bridge = ReservedReleaseArchive(Mock(), ledger)
        bridge.archive.put = Mock(return_value={"ok": True})
        with tempfile.TemporaryDirectory() as root:
            for dirname in ("worker-one", "worker-two"):
                folder = Path(root, dirname)
                folder.mkdir()
                Path(folder, "video.mp4").write_bytes(b"same-video")
                bridge.put(folder)
        self.assertEqual(len(identities), 2)
        self.assertEqual(identities[0], identities[1])

if __name__ == "__main__":
    unittest.main()
