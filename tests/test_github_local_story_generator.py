import tempfile
import unittest
from pathlib import Path

from astra_v2.github_local_story_generator import LANES, ROLES, _build_prompt, validate_candidate


def sample():
    lines = [
        "The lighthouse flashed twice, though its keeper was missing.",
        "A rescue boat changed course toward the empty rocks.",
        "Mara sent a third flash using her father's old mirror.",
        "The boat ignored her and turned toward the open sea.",
        "She noticed the lighthouse lens was rotating backward.",
        "Mara reversed its gears and revealed a hidden signal.",
        "The boat returned because the missing keeper had warned them.",
    ]
    return {
        "title": "The Lighthouse That Signaled Back",
        "premise": ("A coastal village relies on a lighthouse whose keeper vanished before a storm. "
                    "A young mechanic discovers the light is sending a warning through an old gear system. "
                    "Her attempt to call for help makes the rescue boat move farther away, forcing her "
                    "to understand the signal before the storm reaches the harbor."),
        "question": "Would you have trusted the strange signal or turned the boat around?",
        "performance_scenes": [
            {"role": role, "speech": speech}
            for role, speech in zip(ROLES, lines)
        ],
    }


class GithubLocalStoryGeneratorTests(unittest.TestCase):
    def test_accepts_valid_seven_beat_story(self):
        result = validate_candidate(sample())
        self.assertEqual(len(result["performance_scenes"]), 7)
        self.assertGreaterEqual(result["word_count"], 65)
        self.assertLessEqual(result["word_count"], 85)

    def test_rejects_wrong_role_order(self):
        item = sample()
        item["performance_scenes"][0]["role"] = "stakes"
        with self.assertRaisesRegex(ValueError, "role hook"):
            validate_candidate(item)

    def test_rejects_generic_engagement(self):
        item = sample()
        item["question"] = "Please like and subscribe to see more stories?"
        with self.assertRaises(ValueError):
            validate_candidate(item)

    def test_rejects_repeated_premise(self):
        item = sample()
        history = [{"premise": item["premise"], "fingerprint": "old"}]
        with self.assertRaisesRegex(ValueError, "too similar"):
            validate_candidate(item, history)

    def test_content_catalog_includes_requested_formats(self):
        for lane in ("weird_facts", "history_gk", "india_gk", "space_facts",
                     "brain_puzzle", "riddle", "quick_quiz", "spot_the_lie",
                     "two_truths_one_lie", "what_if", "current_news", "trending_topics"):
            self.assertIn(lane, LANES)

    def test_current_news_prompt_requires_source_pack(self):
        prompt = _build_prompt("current_news", [], 42, [
            {"title": "A verified headline", "url": "https://example.com/story"}
        ])
        self.assertIn("Use ONLY the supplied source pack", prompt)
        self.assertIn("Do not invent dates, numbers", prompt)

    def test_puzzle_prompt_delays_answer(self):
        prompt = _build_prompt("brain_puzzle", [], 42)
        self.assertIn("place the answer after a clear thinking pause", prompt)
        self.assertIn("Never use an ambiguous trick answer", prompt)

    def test_rejects_short_spoken_script(self):
        item = sample()
        item["performance_scenes"][0]["speech"] = "It was dark."
        with self.assertRaisesRegex(ValueError, "6–14 words"):
            validate_candidate(item)


if __name__ == "__main__":
    unittest.main()
