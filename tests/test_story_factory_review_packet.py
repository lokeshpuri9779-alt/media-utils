import unittest
from astra_v2.story_factory import candidate_at, screen_candidate
from astra_v2.story_factory_review_packet import build_packet


class FactoryPacketIntegrityTests(unittest.TestCase):
    def test_packet_retains_source_digest_and_never_approves(self):
        candidate = candidate_at(0)
        packet = build_packet([candidate], [screen_candidate(candidate)])
        self.assertEqual(packet["approved_count"], 0)
        self.assertEqual(len(packet["candidates"][0]["source_sha256"]), 64)
        self.assertFalse(packet["candidates"][0]["eligible_for_automatic_publishing"])

    def test_premise_mismatch_fails_closed(self):
        candidate = candidate_at(0)
        review = screen_candidate(candidate)
        review["premise_key"] = "different"
        with self.assertRaisesRegex(ValueError, "premise_mismatch"):
            build_packet([candidate], [review])

    def test_duplicate_identity_fails_closed(self):
        candidate = candidate_at(0)
        review = screen_candidate(candidate)
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            build_packet([candidate, candidate], [review, review])


if __name__ == "__main__":
    unittest.main()
