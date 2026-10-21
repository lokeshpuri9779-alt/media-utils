import unittest
from astra_v2.gemini_batch_review import review_batch
from astra_v2.editorial_approval_manifest import story_digest


class ReviewBatchTests(unittest.TestCase):
    def test_rejection_never_exports(self):
        story = {"content_id": "s1", "kind": "microfiction"}
        stories, reviews, audit = review_batch({"status": "unreviewed", "stories": [story]}, [],
            reviewer=lambda s, h: {"approved": False, "record": None, "issues": ["review_failed:HTTP_429"]})
        self.assertEqual(stories["stories"], [])
        self.assertEqual(reviews["reviews"], [])
        self.assertEqual(audit["reviews"][0]["issues"], ["review_failed:HTTP_429"])

    def test_reviewer_receives_authored_candidate(self):
        story = {"content_id": "s1", "kind": "microfiction"}
        observed = []
        def reviewer(candidate, history):
            observed.append(candidate["kind"])
            return {"approved": False, "record": None, "issues": ["editorial_reject"]}
        review_batch({"status": "unreviewed", "stories": [story]}, [], reviewer=reviewer)
        self.assertEqual(observed, ["authored_causal_story"])
        self.assertEqual(story["kind"], "microfiction")

    def test_mismatched_digest_never_exports(self):
        story = {"content_id": "s1"}
        stories, reviews, audit = review_batch({"status": "unreviewed", "stories": [story]}, [],
            reviewer=lambda s, h: {"approved": True, "record": {"story_sha256": "bad"}, "issues": []})
        self.assertEqual(stories["stories"], [])
        self.assertFalse(audit["reviews"][0]["approved"])


if __name__ == "__main__":
    unittest.main()
