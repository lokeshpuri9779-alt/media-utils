"""Reject known story actions that Studio's isolated subject icons cannot show.

This is a capability check, not a claim of general semantic/video review.
Exact scene artwork must still pass the existing asset loader and compositor.
"""
import re

from astra_errors import CreativeReject

_HUMAN = re.compile(
    r"\b(?:stationmaster|courier|thief|thieves|man|woman|boy|girl|"
    r"child|children|person|people|guard|passenger|driver|captain)\b", re.I)
_INTERACTION = re.compile(
    r"\b(?:slides?|sliding|maneuvers?|manoeuvres?|navigates?|"
    r"enters?|entering|retrieves?|retrieving|returns?|returning|"
    r"drops?|dropping|hands?|handing|grabs?|grabbing|"
    r"intercepts?|intercepting|hiding|chases?|chasing)\b", re.I)
_SIGNAL = re.compile(r"\b(?:signal|transmission|radio|frequency|waveform|broadcast|beacon)\b", re.I)


_BIOLOGICAL_HUMAN = re.compile(
    r"\b(?:human|person|child|boy|girl|man|woman|teenager|adult|male|female|"
    r"student|pilot|officer|engineer|botanist)\b", re.I)
_MECHANICAL_CHARACTER = re.compile(r"\b(?:robot|android|automaton|drone|machine)\b", re.I)

# Two independent visual cues identify a visibly embodied figure even when
# an AI story omitted its visual_bible. Generic forest/door/signal icons cannot
# portray a clothed character performing an action.
_FIGURE_APPEARANCE = re.compile(
    r"\\b(?:hair|tunic|vest|shirt|trousers|cloak|coat|boots|goggles|cheek)\\b", re.I)
_FIGURE_ACTION = re.compile(
    r"\\b(?:pointing|kneeling|standing|stands?|holding|holds?|smiling|"
    r"walking|wearing|wears?|tipping|pouring|running|gripping)\\b", re.I)


def named_human_characters(visual_bible):
    """Identify explicit named people; never guess human identity from a name."""
    if not isinstance(visual_bible, dict):
        return ()
    characters = visual_bible.get("characters")
    if not isinstance(characters, dict):
        return ()
    names = []
    for name, description in characters.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(description, str):
            continue
        if not _BIOLOGICAL_HUMAN.search(description):
            continue
        # A female robot or humanoid machine is not automatically a human.
        if (_MECHANICAL_CHARACTER.search(description)
                and not re.search(r"\bhuman\b", description, re.I)):
            continue
        names.append(name.strip())
    return tuple(names)


def directed_scene_issue(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "visual_intent", "action"))
    # A named child/person in the authored visual bible must not disappear
    # into a generic tree, door or signal icon. The existing verified-scene-art
    # exception remains available through validate_directed_scene.
    named_humans = shot.get("story_named_humans")
    for name in (named_humans if isinstance(named_humans, (tuple, list)) else ()):
        if (isinstance(name, str) and name.strip()
                and re.search(r"(?<!\w)" + re.escape(name.strip()) + r"(?!\w)", text, re.I)):
            return "human_actor_not_supported_by_directed_icons"
    # Include the story title so first-person/pronoun beats don't erase humans.
    if _HUMAN.search(text + " " + str(shot.get("story_title") or "")):
        return "human_actor_not_supported_by_directed_icons"
    visual_prompt = str(shot.get("visual_prompt") or "")
    if (_FIGURE_APPEARANCE.search(visual_prompt)
            and _FIGURE_ACTION.search(visual_prompt)):
        return "embodied_character_not_supported_by_directed_icons"
    if str(shot.get("visual") or "").lower() == "signal" and not _SIGNAL.search(text):
        return "signal_graphic_does_not_depict_narrated_event"
    subject = str(shot.get("story_subject") or shot.get("visual") or "").lower()
    if subject in {"robot", "train"} and _INTERACTION.search(text):
        return "subject_icon_cannot_depict_narrated_interaction"
    return None


def validate_directed_scene(shot):
    issue = directed_scene_issue(shot)
    if not issue:
        return
    # A path, tags, or foreground prop alone are not a complete scene.
    if all(shot.get(k) for k in ("artwork_asset_id", "artwork_manifest_path",
                                "story_content_id", "scene_id")):
        from astra.asset_library import select_asset
        asset = select_asset(shot, shot["artwork_manifest_path"])
        if (asset and asset.get("category") == "background"
                and asset.get("sha256")
                and asset.get("source") != "offline-semantic-generator"):
            return
    raise CreativeReject("Directed scene requires verified scene artwork: " + issue)
