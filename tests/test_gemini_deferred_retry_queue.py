"""Provider-free deferred Gemini retry queue invariants."""
import copy
import unittest

from astra_v2.gemini_deferred_archive import build_archive
from astra_v2.gemini_deferred_retry_queue import (
    DEFAULT_COOLDOWN_SECONDS,
    MAX_ATTEMPTS,
    QUEUE_STATUS,
    STATE_STATUS,
    empty_retry_state,
    prepare_retry_batch,
    record_attempts_after_provider_call,
)


def make_archive(count=3):
    stories = [
        {"content_id": "deferred-" + str(i), "kind": "microfiction",
         "title": "Draft " + str(i), "production_ready": True}
        for i in range(count)
    ]
    proposals = {"status": "unreviewed", "stories": stories}
    audit = {"reviews": [
        {"content_id": story["content_id"], "approved": False,
         "issues": ["review_deferred:rate_limited"]}
        for story in stories
    ]}
    archive, added = build_archive(proposals, audit, run_id="123")
    assert added == count
    return archive


class GeminiDeferredRetryQueueTests(unittest.TestCase):
    def test_prepare_seeds_tracking_but_never_consumes_attempts(self):
        archive = make_archive()
        original = empty_retry_state()
        snapshot = copy.deepcopy(original)
        queue, state = prepare_retry_batch(archive, original, now=1000)
        self.assertEqual(queue["status"], QUEUE_STATUS)
        self.assertEqual(queue["selected_count"], 3)
        self.assertEqual([row["attempts_so_far"] for row in queue["entries"]],
                         [0, 0, 0])
        self.assertEqual([row["attempts"] for row in state["entries"]],
                         [0, 0, 0])
        self.assertEqual(original, snapshot)
        self.assertFalse(queue["provider_requests_enabled"])
        self.assertFalse(queue["editorial_approval"])
        self.assertFalse(queue["publication_approval"])
        self.assertFalse(queue["eligible_for_automatic_publishing"])
        self.assertFalse(state["provider_requests_enabled"])
        self.assertFalse(state["publication_approval"])

    def test_cooldown_and_two_attempt_ceiling_are_enforced(self):
        archive = make_archive(1)
        queue, state = prepare_retry_batch(archive, now=1000)
        digest = queue["entries"][0]["source_sha256"]

        # This helper records a request already dispatched by a future adapter;
        # it does not make the request itself.
        state = record_attempts_after_provider_call(
            state, [digest], attempted_at=1000)
        early, unchanged = prepare_retry_batch(
            archive, state, now=1000 + DEFAULT_COOLDOWN_SECONDS - 1)
        self.assertEqual(early["selected_count"], 0)
        self.assertEqual(unchanged["entries"][0]["attempts"], 1)

        eligible, _ = prepare_retry_batch(
            archive, state, now=1000 + DEFAULT_COOLDOWN_SECONDS)
        self.assertEqual(eligible["selected_count"], 1)
        self.assertEqual(eligible["entries"][0]["attempts_so_far"], 1)

        state = record_attempts_after_provider_call(
            state, [digest],
            attempted_at=1000 + DEFAULT_COOLDOWN_SECONDS)
        self.assertEqual(state["entries"][0]["attempts"], MAX_ATTEMPTS)
        exhausted, _ = prepare_retry_batch(
            archive, state, now=1000 + 2 * DEFAULT_COOLDOWN_SECONDS)
        self.assertEqual(exhausted["selected_count"], 0)

    def test_attempt_recording_rejects_early_duplicate_unknown_and_over_limit(self):
        archive = make_archive(1)
        queue, state = prepare_retry_batch(archive, now=200)
        digest = queue["entries"][0]["source_sha256"]
        with self.assertRaisesRegex(ValueError, "invalid_attempt_source_hashes"):
            record_attempts_after_provider_call(
                state, [digest, digest], attempted_at=200)
        with self.assertRaisesRegex(ValueError, "unknown_retry_source_hash"):
            record_attempts_after_provider_call(state, ["f" * 64], attempted_at=200)
        state = record_attempts_after_provider_call(
            state, [digest], attempted_at=200)
        with self.assertRaisesRegex(ValueError, "cooldown_not_elapsed"):
            record_attempts_after_provider_call(
                state, [digest], attempted_at=201)
        state = record_attempts_after_provider_call(
            state, [digest], attempted_at=200 + DEFAULT_COOLDOWN_SECONDS)
        with self.assertRaisesRegex(ValueError, "attempt_limit_reached"):
            record_attempts_after_provider_call(
                state, [digest],
                attempted_at=200 + 2 * DEFAULT_COOLDOWN_SECONDS)

    def test_batch_limit_and_hard_safety_ceilings(self):
        archive = make_archive(3)
        queue, _ = prepare_retry_batch(archive, now=10, limit=2)
        self.assertEqual(queue["selected_count"], 2)
        with self.assertRaisesRegex(ValueError, "limit_exceeds"):
            prepare_retry_batch(archive, now=10, limit=11)
        with self.assertRaisesRegex(ValueError, "max_attempts_exceeds"):
            prepare_retry_batch(archive, now=10, max_attempts=3)
        with self.assertRaisesRegex(ValueError, "max_attempts_exceeds"):
            record_attempts_after_provider_call(
                empty_retry_state(), ["f" * 64], attempted_at=10,
                max_attempts=3)

    def test_source_digest_and_archive_approval_flags_are_verified(self):
        archive = make_archive(1)
        tampered = copy.deepcopy(archive)
        tampered["entries"][0]["proposal"]["title"] = "Changed"
        with self.assertRaisesRegex(ValueError, "source_mismatch"):
            prepare_retry_batch(tampered, now=10)
        promoted = copy.deepcopy(archive)
        promoted["publication_approval"] = True
        with self.assertRaisesRegex(ValueError, "metadata"):
            prepare_retry_batch(promoted, now=10)

    def test_state_identity_and_metadata_fail_closed(self):
        archive = make_archive(1)
        queue, state = prepare_retry_batch(archive, now=10)
        digest = queue["entries"][0]["source_sha256"]
        changed = copy.deepcopy(state)
        changed["entries"][0]["content_id"] = "wrong-id"
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            prepare_retry_batch(archive, changed, now=10)
        approved = copy.deepcopy(state)
        approved["editorial_approval"] = True
        with self.assertRaisesRegex(ValueError, "invalid_retry_tracking_state"):
            prepare_retry_batch(archive, approved, now=10)
        duplicate = copy.deepcopy(state)
        duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
        with self.assertRaisesRegex(ValueError, "invalid_retry_tracking_entry"):
            prepare_retry_batch(archive, duplicate, now=10)
        self.assertEqual(len(digest), 64)

    def test_explicit_clock_and_parameters_reject_invalid_values(self):
        archive = make_archive(1)
        for now in (True, -1, 1.5, "100"):
            with self.subTest(now=now), self.assertRaises(ValueError):
                prepare_retry_batch(archive, now=now)
        with self.assertRaisesRegex(ValueError, "invalid_cooldown_seconds"):
            prepare_retry_batch(archive, now=100, cooldown_seconds=-1)

    def test_future_last_attempt_does_not_become_eligible(self):
        archive = make_archive(1)
        queue, state = prepare_retry_batch(archive, now=100)
        digest = queue["entries"][0]["source_sha256"]
        state = record_attempts_after_provider_call(
            state, [digest], attempted_at=500)
        before, _ = prepare_retry_batch(archive, state, now=499)
        self.assertEqual(before["selected_count"], 0)

    def test_tracking_state_and_queue_are_not_publisher_inputs(self):
        self.assertEqual(STATE_STATUS, "retry_tracking_only")
        self.assertEqual(QUEUE_STATUS, "retry_queue_review_only")
        self.assertFalse(empty_retry_state()["eligible_for_automatic_publishing"])


if __name__ == "__main__":
    unittest.main()
