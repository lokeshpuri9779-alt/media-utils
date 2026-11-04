"""Adversarial checks for the reusable frog review-only CI boundary."""
from pathlib import Path
import unittest

from tools.experimental_frog_workflow_boundary import (
    REVIEW_WORKFLOW, PUBLISHER, PRELOAD, boundary_errors
)

ROOT = Path(__file__).resolve().parents[1]


class FrogReviewBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = (ROOT / REVIEW_WORKFLOW).read_text()
        cls.publisher = (ROOT / PUBLISHER).read_text()
        cls.preload = (ROOT / PRELOAD).read_text()

    def check(self, review=None, publisher=None, preload=None):
        return boundary_errors(
            self.review if review is None else review,
            self.publisher if publisher is None else publisher,
            self.preload if preload is None else preload,
        )

    def test_current_review_is_isolated(self):
        self.assertEqual(self.check(), [])

    def test_publishing_permission_rejected(self):
        bad = self.review.replace(
            "permissions:\n  contents: read",
            "permissions:\n  contents: write", 1)
        self.assertIn("read-only", " ".join(self.check(review=bad)))

    def test_broad_trigger_rejected(self):
        bad = self.review.replace(
            "      - tools/experimental_frog_story_render.py",
            "      - '**'", 1)
        self.assertIn("allowlist", " ".join(self.check(review=bad)))

    def test_publisher_access_to_frog_rejected(self):
        bad = self.publisher + "\n# tools/experimental_frog_story_render.py\n"
        self.assertIn("leaked", " ".join(self.check(publisher=bad)))

    def test_preload_artifact_consumption_rejected(self):
        bad = self.preload + "\n# astra-frog-story-review\n"
        self.assertIn("leaked", " ".join(self.check(preload=bad)))

    def test_secrets_rejected(self):
        bad = self.review + "\n# ${{ secrets.YOUTUBE_TOKEN }}\n"
        self.assertIn("secrets", " ".join(self.check(review=bad)))

    def test_extra_action_rejected(self):
        bad = self.review.replace(
            "      - uses: actions/checkout@v4",
            "      - uses: actions/checkout@v4\n      - uses: example/publish@v1",
            1)
        self.assertIn("unapproved", " ".join(self.check(review=bad)))

    def test_old_branch_only_regression_rejected(self):
        bad = self.review.replace("      - main", "      - validation/astra-frog-post-merge", 1)
        self.assertIn("main only", " ".join(self.check(review=bad)))

    def test_missing_pixel_gate_rejected(self):
        bad = self.review.replace(
            "python3 -m tools.experimental_frog_object_pixel_tracks",
            "echo skipped-pixel-tracks", 1)
        self.assertIn("fail-closed", " ".join(self.check(review=bad)))

    def test_unsafe_schedule_event_rejected(self):
        bad = self.review.replace(
            "  workflow_dispatch:\n",
            "  workflow_dispatch:\n  schedule:\n    - cron: '*/5 * * * *'\n", 1)
        self.assertIn("only push", " ".join(self.check(review=bad)))


if __name__ == "__main__":
    unittest.main()
