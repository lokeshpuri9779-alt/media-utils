import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from astra_errors import CreativeReject
from astra_v2.unified_story_engine import validate_story_shot, draw_story_frame


class DirectedSceneContractTests(unittest.TestCase):
    def test_stationmaster_video_beats_cannot_pass_as_icons(self):
        beats = [
            ("signal", None, "The manifest is gone from my desk and the express locks the platform gates."),
            ("robot", "robot", "My small mechanical helper, Unit Seven, can slide through the narrow vent to find where the thief went."),
            ("robot", "robot", "The drone hums softly as it maneuvers through the tunnel."),
            ("train", "train", "The drone drops the stolen papers into my waiting hands just as the locomotive begins its forward roll."),
        ]
        for visual, subject, speech in beats:
            with self.subTest(visual=visual, speech=speech):
                shot = dict(visual=visual, story_subject=subject, speech=speech)
                with self.assertRaises(CreativeReject):
                    validate_story_shot(shot)
                renderer = Mock()
                with self.assertRaises(CreativeReject):
                    draw_story_frame(object(), shot, .2, draw_directed=renderer,
                                     global_time=.2, accent=(100, 100, 100))
                renderer.assert_not_called()

    def test_title_retains_human_context_for_first_person_speech(self):
        with self.assertRaises(CreativeReject):
            validate_story_shot({"story_title": "The Stationmaster's Missing Courier",
                                 "speech": "I waited beside the desk.", "visual": "clock"})

    def test_supported_environment_signal_and_animal_routes_remain(self):
        for shot in ({"speech": "The city lost its gravity.", "visual": "city"},
                     {"speech": "The radio signal fades.", "visual": "signal"},
                     {"speech": "The train rolls along the railway.", "visual": "train"}):
            self.assertEqual(validate_story_shot(shot), "directed")
        self.assertEqual(validate_story_shot({"speech": "The owl grabbed the lantern."}), "solo")

    def test_beacon_is_valid_signal_but_ordinary_light_is_not(self):
        self.assertEqual(validate_story_shot({
            "visual": "signal",
            "speech": "She repaired the beacon so nobody would be forgotten again.",
        }), "directed")
        with self.assertRaises(CreativeReject):
            validate_story_shot({
                "visual": "signal",
                "speech": "She lit a lantern so nobody would be forgotten again.",
            })
        from astra.artwork_story_bridge import build_story
        review = build_story("astra/fixtures/artwork_storyboard_review.json")
        for beat in review["story_beats"]:
            with self.subTest(beat=beat["headline"]):
                self.assertEqual(validate_story_shot(beat), "directed")

    def test_named_child_from_visual_bible_cannot_be_replaced_by_forest_icon(self):
        from astra_v2.directed_scene_contract import named_human_characters
        from astra_v2.renderer_eligibility import check_renderer_eligibility
        bible = {"characters": {
            "Leo": "A seven-year-old child with messy brown hair and a green sweater.",
            "Unit 7G": "A gentle female caretaker robot with copper plating.",
        }}
        self.assertEqual(named_human_characters(bible), ("Leo",))
        self.assertEqual(named_human_characters({"characters": {
            "Unit 7G": "A female robot with a blue visor."}}), ())
        with self.assertRaisesRegex(CreativeReject, "human_actor_not_supported"):
            validate_story_shot({"visual": "forest",
                                 "visual_prompt": "Leo chases butterflies across the meadow.",
                                 "story_named_humans": ("Leo",)})
        story = {
            "genre": "fiction", "content_id": "named-child-fidelity",
            "title": "The Caretaker's Last Secret at Cedar Grove",
            "visual_bible": bible,
            "story_beats": [
                {"headline": "The Hidden Diagnosis", "visual": "robot",
                 "speech": "Unit 7G hides the medical log for young Leo.",
                 "visual_prompt": "Unit 7G holds a tablet beside Leo's bed."},
                {"headline": "The Inspection", "visual": "signal",
                 "speech": "The auditors transmit a warning signal.",
                 "visual_prompt": "A radio terminal broadcasts a warning."},
                {"headline": "The Override", "visual": "door",
                 "speech": "The caretaker opens the cabin door.",
                 "visual_prompt": "Unit 7G opens the cabin door."},
                {"headline": "The Meadow", "visual": "forest",
                 "speech": "Leo chases butterflies across the meadow.",
                 "visual_prompt": "Leo runs through bright grass with a paper pinwheel."},
            ],
        }
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}):
            eligible, reason, _ = check_renderer_eligibility(story)
        self.assertFalse(eligible)
        self.assertIn("human_actor_not_supported_by_directed_icons", reason)

    def test_icebound_researcher_requires_real_scene_art(self):
        # The independently approved 2026-10-31 Gemini story had no verified
        # scene artwork: its meteorologist/researcher characters were silently
        # treated as icon-only backgrounds by the preflight.
        from astra_v2.directed_scene_contract import named_human_characters
        from astra_v2.renderer_eligibility import check_renderer_eligibility
        bible = {"characters": {
            "Dr. Vane": "A determined meteorologist with weathered skin and a navy-blue polar parka.",
            "Colleague": "A field researcher wearing an orange insulated snowsuit.",
            "Unit 7G": "An autonomous researcher robot with steel plating.",
        }}
        self.assertEqual(named_human_characters(bible), ("Dr. Vane", "Colleague"))
        story = {
            "genre": "fiction",
            "content_id": "rayvan-gemini-c4da68efcf8034b2d9b5",
            "title": "The Icebound Navigator and the Fissure Beacon",
            "visual_bible": bible,
            "story_beats": [{
                "headline": "The Hidden Fault",
                "visual": "signal",
                "speech": "The sensor array shows his beacon dropping deeper into the shelf.",
                "visual_prompt": "Dr. Vane stands inside the command dome pointing at a red telemetry screen.",
            }],
        }
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}):
            eligible, reason, _ = check_renderer_eligibility(story)
        self.assertFalse(eligible)
        self.assertIn("human_actor_not_supported_by_directed_icons", reason)

    def test_clothed_character_action_without_bible_needs_exact_art(self):
        # Publisher run 40798871334 composited only forest backdrops for a
        # Gemini scene describing Bramble and Rowan as embodied characters.
        shot = {
            "visual": "forest",
            "speech": "Look at the central leaves, Rowan!",
            "visual_prompt": (
                "Bramble pointing at a withered root system in a towering tree. "
                "Bramble has messy auburn hair and a moss-green tunic. "
                "Rowan stands beside him holding a rusted metal trowel."
            ),
        }
        with self.assertRaisesRegex(
                CreativeReject, "embodied_character_not_supported_by_directed_icons"):
            validate_story_shot(shot)
        self.assertEqual(validate_story_shot({
            "visual": "forest", "speech": "The forest glows after rain.",
            "visual_prompt": "Sunlight filters through the forest canopy.",
        }), "directed")

    def test_gemini_story_with_clothed_actor_fails_publication_preflight(self):
        from astra_v2.renderer_eligibility import check_renderer_eligibility
        story = {
            "genre": "fiction",
            "content_id": "fidelity-regression-no-visual-bible",
            "title": "The Canopy Trackers and the Fading Roots",
            "story_beats": [{
                "headline": "Discovering the Wilted Core",
                "speech": "Look at the central leaves, Rowan!",
                "visual": "forest",
                "visual_prompt": (
                    "Bramble pointing at a withered root system. "
                    "Bramble has messy auburn hair and a moss-green tunic. "
                    "Rowan stands beside him holding a rusted trowel."
                ),
            }],
        }
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}):
            eligible, reason, _ = check_renderer_eligibility(story)
        self.assertFalse(eligible)
        self.assertIn("embodied_character_not_supported_by_directed_icons", reason)

    def test_manifest_path_and_foreground_props_do_not_override_check(self):
        shot = {"speech": "The thief grabs the papers.", "visual": "robot",
                "artwork_manifest_path": "/missing/manifest.json"}
        with self.assertRaises(CreativeReject):
            validate_story_shot(shot)

    def test_exact_scene_art_is_verified_and_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            art = root / "art/scene.png"
            Image.new("RGB", (40, 70), "blue").save(art)
            row = dict(id="scene-one", path="art/scene.png", status="approved",
                       source="original-manual", category="background", tags=[],
                       story_content_id="station", scene_id="001",
                       sha256=hashlib.sha256(art.read_bytes()).hexdigest())
            manifest = root / "art/manifest.json"
            shot = dict(visual="robot", speech="The thief grabs the papers.",
                        artwork_asset_id="scene-one", artwork_manifest_path=str(manifest),
                        story_content_id="station", scene_id="001")
            def save():
                manifest.write_text(json.dumps({"assets": [row]}))
            save()
            self.assertEqual(validate_story_shot(shot), "directed")
            for key, value in (("scene_id", "002"), ("category", "prop"),
                               ("source", "offline-semantic-generator")):
                old = row[key]
                row[key] = value
                save()
                with self.subTest(key=key), self.assertRaises(CreativeReject):
                    validate_story_shot(shot)
                row[key] = old
            save()
            art.write_bytes(b"corrupt")
            with self.assertRaises(CreativeReject):
                validate_story_shot(shot)

    def test_full_render_rejects_before_voice_or_encoding(self):
        import studio_renderer
        story = dict(genre="fiction", content_id="station-regression",
                     title="The Stationmaster and the Missing Midnight Courier",
                     story_beats=[dict(headline="Discovery", visual="signal",
                                       speech="The manifest is gone from my desk.")])
        with patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"}), \
             patch.object(studio_renderer, "creative_quality_gate", return_value={}), \
             patch.object(studio_renderer, "voice_plan") as voice:
            with self.assertRaisesRegex(CreativeReject, "requires verified scene artwork"):
                studio_renderer.render_short(story, "/unused/short.mp4")
            voice.assert_not_called()


if __name__ == "__main__":
    unittest.main()
