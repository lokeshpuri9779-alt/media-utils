import unittest

from astra_v2.github_storage_policy import (
    ACTIONS_ARTIFACT_LIMIT,
    GIB,
    MIB,
    GitHubStoragePolicy,
)


class GitHubStoragePolicyTests(unittest.TestCase):
    def test_default_denies(self):
        self.assertFalse(GitHubStoragePolicy().admission(MIB)["admitted_snapshot_only"])

    def test_release_budget_and_reservations(self):
        policy = GitHubStoragePolicy(
            releases_budget_bytes=100 * MIB,
            releases_used_bytes=60 * MIB,
            reserved_bytes=10 * MIB,
        )
        self.assertTrue(policy.admission(30 * MIB)["admitted_snapshot_only"])
        self.assertFalse(policy.admission(31 * MIB)["admitted_snapshot_only"])

    def test_single_asset_limit(self):
        policy = GitHubStoragePolicy(releases_budget_bytes=4 * GIB)
        self.assertFalse(policy.admission(2 * GIB + 1)["admitted_snapshot_only"])

    def test_actions_budget(self):
        policy = GitHubStoragePolicy(actions_budget_bytes=100 * MIB)
        self.assertTrue(policy.admission(MIB, kind="actions")["admitted_snapshot_only"])
        self.assertFalse(policy.admission(101 * MIB, kind="actions")["admitted_snapshot_only"])
        with self.assertRaises(ValueError):
            GitHubStoragePolicy(actions_budget_bytes=ACTIONS_ARTIFACT_LIMIT + 1)

    def test_reject_invalid_values(self):
        with self.assertRaises(ValueError):
            GitHubStoragePolicy(releases_used_bytes=-1)
        with self.assertRaises(ValueError):
            GitHubStoragePolicy().admission(0)
        with self.assertRaises(ValueError):
            GitHubStoragePolicy().admission(True)
        with self.assertRaises(ValueError):
            GitHubStoragePolicy().admission(MIB, kind="unknown")

    def test_explicitly_not_atomic_or_billing_guaranteed(self):
        result = GitHubStoragePolicy(releases_budget_bytes=MIB).admission(MIB)
        self.assertFalse(result["concurrency_safe"])
        self.assertFalse(result["provider_billing_guaranteed"])
        self.assertFalse(result["publication_triggered"])


if __name__ == "__main__":
    unittest.main()
