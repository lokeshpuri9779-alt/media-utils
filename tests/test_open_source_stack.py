import unittest

from oss_stack import COMPONENTS, PERMISSIVE, direct_use_allowed, policy_report


class OpenSourceStackTests(unittest.TestCase):
    def test_direct_components_are_permissive(self):
        for name, item in COMPONENTS.items():
            if direct_use_allowed(name):
                self.assertIn(item["license"], PERMISSIVE)

    def test_restricted_or_unknown_components_are_not_direct(self):
        for name in ("remotion", "openmontage", "video2x"):
            self.assertFalse(direct_use_allowed(name))

    def test_policy_report_is_fail_closed(self):
        report = policy_report()
        self.assertIn("review_required", report)
        self.assertIn("remotion", report["review_required"])


if __name__ == "__main__":
    unittest.main()
