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
_SIGNAL = re.compile(r"\b(?:signal|transmission|radio|frequency|waveform|broadcast)\b", re.I)


def directed_scene_issue(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "visual_intent", "action"))
    # Include the story title so first-person/pronoun beats don't erase humans.
    if _HUMAN.search(text + " " + str(shot.get("story_title") or "")):
        return "human_actor_not_supported_by_directed_icons"
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
