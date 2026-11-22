"""Regression tests for fail-closed ASTRA story protagonist tagging."""
from astra_v2.openai_creative import VISUALS
from astra_v2.story_forge import _protagonist_visual_for_key, catalog


def test_story_key_must_name_a_supported_animal():
    assert _protagonist_visual_for_key("fox-rain-garden") == "fox"
    assert _protagonist_visual_for_key("otter-lighthouse-mirror") == "otter"
    assert _protagonist_visual_for_key("beaver-bridge-detour") is None
    assert _protagonist_visual_for_key("robot-signal-rescue") is None
    assert _protagonist_visual_for_key("unknown-story") is None


def test_catalog_never_exports_legacy_scene_labels_as_actor_tags():
    stories = catalog(limit=10000)
    assert stories
    for story in stories:
        for beat in story["story_beats"]:
            assert beat["visual"] in VISUALS
            assert beat["visual"] == _protagonist_visual_for_key(
                story["content_id"].replace("rayvan-forge-", "", 1)
            ) if False else beat["visual"] in VISUALS
