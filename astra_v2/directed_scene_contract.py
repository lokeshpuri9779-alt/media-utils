"""Reject known story actions that Studio's isolated subject icons cannot show.

This is a capability check, not a claim of general semantic/video review.
Exact scene artwork must still pass the existing asset loader and compositor.
"""
import re

from astra_errors import CreativeReject

_HUMAN = re.compile(
    r"\b(?:stationmaster|courier|thief|thieves|man|woman|boy|girl|"
    r"child|children|person|people|guard|passenger|driver|captain|rescuer|explorer|climber|"
    r"doctor|dr|professor|researcher|scientist|"
    r"weaver|miller|loom\s+operator|seamstress|tailor|blacksmith|"
    r"carpenter|fisherman|fisherwoman|shopkeeper|innkeeper|"
    r"potter|baker|farmhand|woodcutter)\b", re.I)
_INTERACTION = re.compile(
    r"\b(?:slides?|sliding|maneuvers?|manoeuvres?|navigates?|"
    r"enters?|entering|retrieves?|retrieving|returns?|returning|"
    r"drops?|dropping|hands?|handing|grabs?|grabbing|"
    r"intercepts?|intercepting|hiding|chases?|chasing)\b", re.I)
_SIGNAL = re.compile(r"\b(?:signal|transmission|radio|frequency|waveform|broadcast|beacon)\b", re.I)

# The current animal puppet library can draw a simple wrench/animal, but
# cannot demonstrate a working railway switch, visible gear engagement,
# heavy winch or sluice mechanism from those icons. An earlier encoded Short
# (rayvan-gemini-4124fe0994195f92cc12) showed a mouse in all sampled beats
# while the narration claimed it freed a signal lever and wedged a gearbox.
# Reject a claimed MECHANICAL OPERATION, not an incidental word like "signal".
_MECHANICAL_RIG = re.compile(
    r"\b(?:signal\s+lever|crank\s+lever|rail(?:way)?\s+switch|"
    r"track\s+switch|gear\s*box|gear\s+teeth|winch|"
    r"sluice\s+gate|floodgate)\b", re.I)
_MECHANICAL_OPERATION = re.compile(
    r"\b(?:stuck|jam(?:s|med|ming)?|wedg(?:e|es|ed|ing)|"
    r"shov(?:e|es|ed|ing)|operat(?:e|es|ed|ing)|"
    r"repair(?:s|ed|ing)?|fix(?:es|ed|ing)?|"
    r"pull(?:s|ed|ing)?|push(?:es|ed|ing)?|"
    r"turn(?:s|ed|ing)?|fasten(?:s|ed|ing)?|"
    r"releas(?:e|es|ed|ing)|lock(?:s|ed|ing)?|"
    r"unlock(?:s|ed|ing)?|lift(?:s|ed|ing)?)\b", re.I)


# Evidence: actual 2026-11-03 Studio Short "Bram and the Frost-Crested
# Pass" depicted an essentially stationary lynx/compass in 24 sampled frames,
# despite a narratively important leap over a chasm, snapped suspension cable,
# fastening wire/latch, and a secured bridge. A puppet jump pose cannot
# establish crossing a geographically real gap or repairing a bridge. These
# are deliberately scoped capability warnings, never semantic pixel approval.
_LARGE_GAP = re.compile(
    r"\b(?:chasm|ravine|abyss|gorge|canyon|"
    r"(?:wide|white|mountain|deep)\s+gap)\b", re.I)
_GAP_CROSSING = re.compile(
    r"\b(?:leap\w*|jump\w*|cross\w*|vault\w*|swing\w*)\b", re.I)
_LARGE_STRUCTURE = re.compile(
    r"\b(?:suspension\s+cable|fraying\s+wire|"
    r"(?:broken|iron|bridge)\s+cable|heavy\s+latch|"
    r"bridge(?:\s+anchor)?|anchor\s+post)\b", re.I)
_STRUCTURE_CHANGED = re.compile(
    r"\b(?:snaps?|snapped|break(?:s|ing)?|broke|fractur\w*|"
    r"collaps\w*|wrapp?\w*|fasten\w*|wedg\w*|"
    r"anchor\w*|secur\w*|lock\w*|repair\w*|"
    r"tension\w*|stabiliz\w*)\b", re.I)


_BIOLOGICAL_HUMAN = re.compile(
    r"\b(?:human|person|child|boy|girl|man|woman|teenager|adult|male|female|"
    r"student|pilot|officer|engineer|botanist|researcher|meteorologist|rescuer|"
    r"weaver|miller|loom\s+operator|seamstress|tailor|blacksmith|"
    r"carpenter|fisherman|fisherwoman|shopkeeper|innkeeper|"
    r"potter|baker|farmhand|woodcutter)\b", re.I)
_MECHANICAL_CHARACTER = re.compile(r"\b(?:robot|android|automaton|drone|machine)\b", re.I)

# Two independent visual cues identify a visibly embodied figure even when
# an AI story omitted its visual_bible. Generic forest/door/signal icons cannot
# portray a clothed character performing an action.
_FIGURE_VISUAL_CUE = re.compile(
    r"\b(?:hair|tunic|vest|shirt|trousers|cloak|coat|boots|goggles|cheek|eyes?|wrist|parka|jackets?|apron|canteen|flask|hammer|trowel|ice\s+axe)\b", re.I)
_FIGURE_ACTION = re.compile(
    r"\b(?:pointing|kneeling|standing|stands?|holding|holds?|smiling|"
    r"walking|wearing|wears?|tipping|pouring|running|gripping|striking|climbing|sitting|swinging)\b", re.I)


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
    if (_FIGURE_VISUAL_CUE.search(visual_prompt)
            and _FIGURE_ACTION.search(visual_prompt)):
        return "embodied_character_not_supported_by_directed_icons"
    if _MECHANICAL_RIG.search(text) and _MECHANICAL_OPERATION.search(text):
        return "unsupported_mechanical_rig_action_requires_scene_art"
    if ((_LARGE_GAP.search(text) and _GAP_CROSSING.search(text))
            or (_LARGE_STRUCTURE.search(text) and _STRUCTURE_CHANGED.search(text))):
        return "unsupported_scene_scale_action_requires_scene_art"
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
