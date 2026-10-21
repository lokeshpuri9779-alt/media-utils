import unittest

from astra_v2.github_storage_ledger import SCHEMA, reserve, settle, release, transact, validate


def state():
    return {"schema": SCHEMA, "capacity_bytes": 100,
            "used_bytes": 10, "reservations": {}}


class StorageLedgerTests(unittest.TestCase):
    def test_reserve_and_settle(self):
        s = reserve(state(), "video-a", 70)
        self.assertEqual(s["reservations"]["video-a"], 70)
        self.assertEqual(reserve(s, "video-a", 70), s)
        with self.assertRaises(RuntimeError):
            reserve(s, "video-b", 21)
        done = settle(s, "video-a", 60)
        self.assertEqual(done["used_bytes"], 70)
        self.assertEqual(done["reservations"], {})
        self.assertEqual(done["settled"]["video-a"], 60)
        with self.assertRaisesRegex(RuntimeError, "already_settled"):
            reserve(done, "video-a", 70)

    def test_invalid_and_overallocation(self):
        with self.assertRaises(ValueError):
            reserve(state(), "a", True)
        with self.assertRaises(ValueError):
            settle(reserve(state(), "a", 20), "a", 21)
        with self.assertRaises(ValueError):
            reserve(reserve(state(), "a", 20), "a", 30)

    def test_zero_byte_settlement_is_exact(self):
        done = settle(reserve(state(), "zero", 20), "zero", 0)
        self.assertEqual(done["used_bytes"], 10)
        self.assertEqual(done["settled"]["zero"], 0)
        with self.assertRaisesRegex(RuntimeError, "already_settled"):
            reserve(done, "zero", 20)

    def test_rejects_settled_history_exceeding_used(self):
        invalid = {**state(), "settled": {"impossible": 11}}
        with self.assertRaisesRegex(ValueError, "settled_history_exceeds_used"):
            validate(invalid)

    def test_release(self):
        self.assertEqual(release(reserve(state(), "a", 10), "a"), state())

    def test_cas_conflict_retries(self):
        remote = {"version": 1, "state": state()}
        attempts = []

        def read():
            return str(remote["version"]), remote["state"].copy()

        def write(expected, new):
            attempts.append(expected)
            if len(attempts) == 1:
                remote["version"] += 1
                remote["state"] = reserve(remote["state"], "other", 30)
                return False
            if expected != str(remote["version"]):
                return False
            remote["version"] += 1
            remote["state"] = new
            return True

        result = transact(read, write, lambda s: reserve(s, "mine", 50))
        self.assertEqual(result["reservations"], {"other": 30, "mine": 50})
        self.assertEqual(len(attempts), 2)

    def test_failed_cas_never_claims_success(self):
        with self.assertRaises(RuntimeError):
            transact(lambda: ("abc", state()), lambda sha, data: False,
                     lambda s: reserve(s, "a", 10), attempts=2)


if __name__ == "__main__":
    unittest.main()
