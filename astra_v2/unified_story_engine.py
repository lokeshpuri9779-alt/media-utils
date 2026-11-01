"""One ASTRA Studio story renderer, combining directed scenes and Pillow acting.

This is a *single* rendering entry point. Solo, duo, group and environmental
compositions are scene grammars, not interchangeable publishing engines.
Unsupported explicit casts and render errors fail closed, without fallback.
No finite renderer can promise faithful depiction of every imaginable story.
"""
from __future__ import annotations

import re

from astra_errors import CreativeReject
from astra_v2.pillow_duo_scene import (
    ACTORS, ALIASES, duo_compatibility, draw_duo, scene_mood, scene_prop,
)
from astra_v2.ensemble_scene import cast_for_shot, ensemble_frame

# A real badger is not in the Studio puppet actor library. A generated
# squirrel-only frame cannot stand in for the narrated badger character.
# Check the title as well as each beat: later pronoun-only beats must not
# silently erase an unsupported protagonist. This is a narrow fail-closed
# regression for the observed public visual mismatch, not semantic approval.
_UNRENDERABLE_BADGER = re.compile(r"\bbadgers?\b", re.IGNORECASE)


def _mentioned_animals(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("speech", "visual_prompt", "action")).lower()
    matches = []
    for species in ACTORS:
        m = re.search(ALIASES[species], text)
        if m:
            matches.append((m.start(), species))
    return tuple(dict.fromkeys(name for _, name in sorted(matches)))


def validate_title_subject(story):
    """Fail closed only when a named animal cannot be rendered faithfully."""
    title = str(story.get("title") or story.get("headline") or "")
    if str(story.get("genre") or "") != "fiction":
        return
    # Recognized animal titles now route through the same unified actor library.
    # Shot-level cast checks still reject incompatible or missing actors.
    if not title.strip():
        raise CreativeReject("Unified Studio: fiction story title missing")


def cast_from_title(title):
    """Recognize a stable 1–8 animal cast in title order, without inventing it."""
    return _mentioned_animals({"speech": str(title)})


def _resolved_cast(shot):
    text_cast = _mentioned_animals(shot)
    if "story_cast" in shot and shot["story_cast"] is not None:
        cast = shot["story_cast"]
        if not isinstance(cast, (tuple, list)):
            raise CreativeReject("Unified Studio: story cast must be a list or tuple")
        names = tuple(str(x).lower().strip() for x in cast)
        if (len(names) > 8 or len(names) != len(set(names))
                or any(x not in ACTORS for x in names)):
            raise CreativeReject("Unified Studio: unsupported, duplicate or oversized cast")
        if any(name not in names for name in text_cast):
            raise CreativeReject("Unified Studio: narration mentions an animal omitted from the declared cast")
        return names
    return text_cast


def validate_story_shot(shot):
    """Return a deliberate scene grammar or reject an incompatible cast."""
    if shot.get("story_human_actor") is not None:
        from astra_v2.human_story_performance import validate_human_scene
        return validate_human_scene(shot)
    identity_text = " ".join(str(shot.get(k) or "") for k in
                             ("story_title", "visual_prompt", "speech", "action"))
    if _UNRENDERABLE_BADGER.search(identity_text):
        raise CreativeReject("Unified Studio: unsupported badger actor requires verified scene artwork")
    cast = _resolved_cast(shot)
    if not cast:
        from astra_v2.directed_scene_contract import validate_directed_scene
        validate_directed_scene(shot)
        return "directed"
    if len(cast) == 1:
        return "solo"
    if len(cast) == 2:
        if not duo_compatibility({**shot, "story_cast": cast})["supported"]:
            raise CreativeReject("Unified Studio: two-character scene not representable")
        return "duo"
    if not cast_for_shot({"story_cast": cast}):
        raise CreativeReject("Unified Studio: ensemble cast not representable")
    return "ensemble"


def _draw_solo(image, shot, t):
    """The same Puppet/Stage actor used for Duo, without an invented partner."""
    from PIL import ImageDraw
    from astra_v2.pillow_duo_scene import _actor, _stage, _prop, prop_position
    from astra_v2.procedural_visual_library import character_recipe, visual_identity
    if image.size != (1080, 1920):
        raise CreativeReject("Unified Studio: solo scene expects 1080x1920")
    cast = _resolved_cast(shot)
    if len(cast) != 1:
        raise CreativeReject("Unified Studio: solo character identity changed")
    draw = ImageDraw.Draw(image)
    _stage(draw, shot, t)
    name = cast[0]
    action = str(shot.get("story_action") or "look").lower()
    prop = scene_prop(shot)
    position = prop_position(action, t)
    from astra_v2.story_motion import smoothstep
    grip = (smoothstep((max(0.0, float(t)) - .06) / .86)
            if prop and action in {"pick", "pickup", "carry", "repair",
                                   "hold", "open", "push", "pull", "catch"}
            else 0.0)
    seed = str(shot.get("story_visual_seed") or name)
    recipe = character_recipe(visual_identity(seed, name, 0))
    _actor(draw, name, 540, 846, t, action, scene_mood(shot), 0,
           hand_target=position if grip else None, hand_strength=grip,
           visual_recipe=recipe)
    if prop:
        _prop(draw, prop, *position, t, action=action)
    return True


def draw_story_frame(image, shot, t, *, draw_directed=None,
                     global_time=None, accent=None):
    """Render the selected grammar; never substitute a different grammar."""
    mode = validate_story_shot(shot)
    cast = _resolved_cast(shot)
    stable_shot = {**shot, "story_cast": cast}
    if mode == "human":
        from astra_v2.human_story_performance import draw_human_scene
        success = draw_human_scene(image, stable_shot, t)
    elif mode == "ensemble":
        stable_shot["experimental_ensemble"] = True
        success = ensemble_frame(image, stable_shot, t)
    elif mode == "duo":
        success = draw_duo(image, stable_shot, t)
    elif mode == "solo":
        success = _draw_solo(image, stable_shot, t)
    else:
        if draw_directed is None or global_time is None or accent is None:
            raise CreativeReject("Unified Studio: directed scene missing storyboard renderer")
        # This is the Studio compositor's first-class environmental/non-animal
        # scene grammar, not an alternative engine or a retry on failure.
        draw_directed(image, stable_shot, global_time, t, accent)
        success = True
    if not success:
        raise CreativeReject("Unified Studio: " + mode + " scene failed to render faithfully")
    if (stable_shot.get("illustrated_assets") is not None
            or stable_shot.get("auto_illustrated_art")):
        from astra_v2.illustrated_story_compositor import apply_story_art
        try:
            apply_story_art(image, stable_shot)
        except (ValueError, OSError) as exc:
            raise CreativeReject("Unified Studio: illustrated artwork rejected: " + str(exc)) from exc
    return mode
