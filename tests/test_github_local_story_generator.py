import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from astra_v2.github_local_story_generator import LANES, ROLES, STRUCTURES, _build_prompt, _candidate_json_schema, _fallback_title, select_engagement_format, creative_direction, validate_candidate
from astra_v2.trend_source_collector import _parse_feed, collect


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

    def test_recovers_short_premise_from_validated_narration(self):
        item = sample()
        item["premise"] = "Too short."
        result = validate_candidate(item)
        self.assertGreaterEqual(len(result["premise"].split()), 35)
        self.assertIn("lighthouse", result["premise"].lower())

    def test_recovers_short_model_title_from_story_premise(self):
        item = sample()
        item["title"] = "Oops"
        result = validate_candidate(item)
        self.assertGreaterEqual(len(result["title"]), 8)
        self.assertIn("Coastal", result["title"])

    def test_title_fallback_handles_unbroken_oversized_title(self):
        result = _fallback_title("X" * 200, sample()["premise"])
        self.assertGreaterEqual(len(result), 8)
        self.assertLessEqual(len(result), 80)
        self.assertIn("coastal", result.lower())

    def test_title_fallback_handles_empty_model_title(self):
        result = _fallback_title("", sample()["premise"])
        self.assertGreaterEqual(len(result), 8)
        self.assertLessEqual(len(result), 80)

    def test_engagement_formats_rotate_deterministically(self):
        first = select_engagement_format("brain_puzzle", 1)
        self.assertEqual(first, select_engagement_format("brain_puzzle", 1))
        self.assertNotEqual(first, select_engagement_format("brain_puzzle", 2))

    def test_generation_schema_requires_exactly_seven_scenes(self):
        schema = _candidate_json_schema()
        scenes = schema["properties"]["performance_scenes"]
        self.assertEqual(scenes["minItems"], 7)
        self.assertEqual(scenes["maxItems"], 7)
        self.assertEqual(scenes["items"]["properties"]["role"]["enum"], ROLES)
        self.assertFalse(scenes["items"]["additionalProperties"])

    def test_lane_schemas_use_compact_puzzle_and_news_structures(self):
        puzzle = _candidate_json_schema("brain_puzzle")["properties"]["performance_scenes"]
        news = _candidate_json_schema("trending_topics")["properties"]["performance_scenes"]
        self.assertEqual(puzzle["minItems"], 4)
        self.assertEqual(puzzle["items"]["properties"]["role"]["enum"],
                         ["challenge", "thinking_pause", "answer", "explanation"])
        self.assertEqual(news["maxItems"], 4)
        self.assertEqual(news["items"]["properties"]["role"]["enum"],
                         ["news_hook", "what_changed", "context", "why_it_matters"])

    def test_compact_puzzle_candidate_validates_with_four_beats(self):
        lines = [
            "A farmer starts with seventeen sheep, but all except nine escape overnight during a storm.",
            "Pause now and decide exactly how many sheep remain safely inside the farmer's field.",
            "The answer is nine, because all but nine means nine sheep stayed behind there.",
            "The wording tests whether you interpret the phrase instead of subtracting every sheep that escaped.",
        ]
        item = {
            "title": "How Many Sheep Actually Remain?",
            "premise": "A short language puzzle asks how many sheep remain after all but nine escape. The wording sounds like a subtraction problem, but its exact meaning gives a much simpler answer. Viewers get a pause to solve it before the reveal explains the phrase.",
            "question": "Did you solve it immediately, or did the wording trick you?",
            "performance_scenes": [
                {"role": role, "speech": speech}
                for role, speech in zip(STRUCTURES["brain_puzzle"], lines)
            ],
        }
        result = validate_candidate(item, lane="brain_puzzle")
        self.assertEqual(len(result["performance_scenes"]), 4)
        self.assertEqual(result["performance_scenes"][0]["role"], "challenge")

    def test_creative_direction_is_deterministic_and_varied(self):
        first = creative_direction("brain_puzzle", 12345)
        self.assertEqual(first, creative_direction("brain_puzzle", 12345))
        self.assertEqual(set(first), {"engagement_format", "tone", "opening_pattern", "payoff_type"})
        samples = [creative_direction("mystery", seed) for seed in range(100, 112)]
        self.assertGreater(len({row["tone"] for row in samples}), 1)
        self.assertGreater(len({row["opening_pattern"] for row in samples}), 1)
        self.assertGreater(len({row["payoff_type"] for row in samples}), 1)

    def test_prompt_contains_distinct_creative_direction(self):
        prompt = _build_prompt("mystery", [], 12345)
        direction = creative_direction("mystery", 12345)
        for value in direction.values():
            self.assertIn(value, prompt)

    def test_prompt_selects_an_engagement_mechanic(self):
        prompt = _build_prompt("brain_puzzle", [], 42)
        self.assertIn("engagement mechanic", prompt)
        self.assertIn(select_engagement_format("brain_puzzle", 42), prompt)
        self.assertIn("performance_scenes must be exactly 4 objects", prompt)
        self.assertNotIn("exactly seven objects", prompt)

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

    def test_nine_direction_batch_lanes_exist_in_generator_catalog(self):
        batch_lanes = {
            "brain_puzzle", "science_explained", "india_gk", "money_business",
            "mystery", "geography_gk", "psychology", "what_if", "trending_topics",
        }
        self.assertTrue(batch_lanes.issubset(LANES))
        self.assertTrue(batch_lanes.issubset(STRUCTURES | {"mystery"}))
        for lane in batch_lanes:
            self.assertTrue(select_engagement_format(lane, 17))

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


    def test_collector_writes_parseable_json_array(self):
        rows = [
            {"title": "Headline one", "url": "https://example.com/one",
             "published": "", "publisher": "Example", "summary": ""},
            {"title": "Headline two", "url": "https://example.com/two",
             "published": "", "publisher": "Example", "summary": ""},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sources.json"
            with patch("astra_v2.trend_source_collector._parse_feed", return_value=rows):
                collected = collect("current_news", str(output))
            parsed = __import__("json").loads(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed, collected)
            self.assertEqual(len(parsed), 2)

    def test_rejects_short_spoken_script(self):
        item = sample()
        item["performance_scenes"][0]["speech"] = "It was dark."
        with self.assertRaisesRegex(ValueError, "6–14 words"):
            validate_candidate(item)


if __name__ == "__main__":
    unittest.main()
