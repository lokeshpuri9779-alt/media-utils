"""ASTRA coordinated offline asset-to-scene pipeline.

Generates reproducible scene assignments, storyboard previews, and an optional
local MP4. This is an experimental production candidate, never a publisher.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops
from astra_v2.character_object_catalog import (
    CHARACTER_COUNT, OBJECT_COUNT, character, prop, draw_character, draw_prop,
)
from astra_v2.storybook_comedy_art import draw_storybook_character, shoulder_anchor as storybook_shoulder_anchor
from astra_v2.cinematic_comedy import camera_frame, draw_gift_surprise, dissolve
from astra_v2.comedy_captions import draw_caption

W, H = 540, 960
BG = (19, 27, 43)


def stable_index(seed, lane, scene, size):
    payload = f"{seed}|{lane}|{scene}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % size


def build_plan(seed, count=12):
    if not seed or not 1 <= count <= 120:
        raise ValueError("seed required; scenes must be 1..120")
    scenes = []
    used_cast, used_props = set(), set()
    for i in range(count):
        ci = stable_index(seed, "character", i, CHARACTER_COUNT)
        oi = stable_index(seed, "object", i, OBJECT_COUNT)
        # Resolve collisions within this plan, deterministically.
        while ci in used_cast:
            ci = (ci + 1) % CHARACTER_COUNT
        while oi in used_props:
            oi = (oi + 1) % OBJECT_COUNT
        used_cast.add(ci)
        used_props.add(oi)
        scenes.append({
            "scene": i + 1, "character_id": ci, "object_id": oi,
            "character": character(ci), "object": prop(oi),
            "duration_seconds": 2.0,
        })
    return {"seed": seed, "scene_count": count, "scenes": scenes,
            "publication_allowed": False, "quality_approved": False}



def build_story_plan(seed, subjects):
    """Build a scene plan only when every requested species can be drawn."""
    from astra_v2.character_object_catalog import SPECIES
    if not isinstance(subjects, list) or not 1 <= len(subjects) <= 120:
        raise ValueError("subjects must be a list of 1..120 species")
    scenes = []
    for i, name in enumerate(subjects):
        if not isinstance(name, str) or name.lower().strip() not in SPECIES:
            raise ValueError(f"scene {i+1}: unsupported subject {name!r}")
        species = name.lower().strip()
        ci = SPECIES.index(species)*100 + stable_index(seed, "role-style", i, 100)
        oi = stable_index(seed, "object", i, OBJECT_COUNT)
        scenes.append({"scene":i+1,"subject":species,"character_id":ci,
                       "object_id":oi,"character":character(ci),"object":prop(oi),
                       "duration_seconds":2.0})
    return {"seed":seed,"scene_count":len(scenes),"scenes":scenes,
            "story_subjects_verified":True,"publication_allowed":False,
            "quality_approved":False}



def build_narrated_plan(seed, narrations):
    """Keep one protagonist across scenes; reject competing named subjects.

    A scene without a named subject inherits the previously established one.
    The first scene must name a supported subject. This intentionally does not
    attempt semantic pronoun resolution or multiple-character staging.
    """
    import re
    from astra_v2.character_object_catalog import SPECIES
    if not isinstance(narrations, list) or not 1 <= len(narrations) <= 120:
        raise ValueError("narrations must contain 1..120 nonempty strings")
    aliases = {"people":"human","person":"human","man":"human","woman":"human",
               "puppy":"dog","kitten":"cat","bunny":"rabbit","penguins":"penguin",
               "foxes":"fox","wolves":"wolf","hedgehogs":"hedgehog"}
    unsupported = {"hedgehog","wolf","wolfhound","squirrel","horse","elephant","shark"}
    subjects = []
    protagonist = None
    for i, narration in enumerate(narrations):
        if not isinstance(narration, str) or not narration.strip():
            raise ValueError(f"scene {i+1}: narration is missing")
        words = set(re.findall(r"[a-z]+", narration.lower()))
        matches = {aliases.get(word, word) for word in words}
        known = matches.intersection(SPECIES)
        missing = matches.intersection(unsupported)
        if missing:
            raise ValueError(f"scene {i+1}: unsupported narrated subject(s) {sorted(missing)}")
        if len(known) > 1:
            raise ValueError(f"scene {i+1}: multiple named species require a multi-character scene")
        if known:
            selected = next(iter(known))
            if protagonist is not None and selected != protagonist:
                raise ValueError(f"scene {i+1}: protagonist changed from {protagonist} to {selected}")
            protagonist = selected
        if protagonist is None:
            raise ValueError(f"scene {i+1}: first scene must name a supported protagonist")
        subjects.append(protagonist)
    plan = build_story_plan(seed, subjects)
    for scene, narration in zip(plan["scenes"], narrations):
        scene["narration"] = narration
    return plan



def build_ensemble_plan(seed, scene_casts):
    """Explicit multi-character casting with stable identities across scenes.

    Each scene names its visible species. Unsupported species, duplicate actors
    and scenes without actors are rejected. This does not infer dialogue roles.
    """
    from astra_v2.character_object_catalog import SPECIES
    if not isinstance(scene_casts, list) or not 1 <= len(scene_casts) <= 120:
        raise ValueError("scene_casts must contain 1..120 scenes")
    registry = {}
    scenes = []
    for i, cast in enumerate(scene_casts):
        if not isinstance(cast, list) or not 1 <= len(cast) <= 4:
            raise ValueError(f"scene {i+1}: expected 1..4 visible actors")
        if any(not isinstance(name, str) or name not in SPECIES for name in cast):
            raise ValueError(f"scene {i+1}: unsupported actor")
        if len(set(cast)) != len(cast):
            raise ValueError(f"scene {i+1}: duplicate actor")
        actors = []
        for name in cast:
            if name not in registry:
                ci = SPECIES.index(name)*100 + stable_index(seed, "actor-"+name, 0, 100)
                registry[name] = ci
            ci = registry[name]
            actors.append({"subject":name,"character_id":ci,"character":character(ci)})
        oi = stable_index(seed, "object", i, OBJECT_COUNT)
        scenes.append({"scene":i+1,"actors":actors,"subject":actors[0]["subject"],
                       "character_id":actors[0]["character_id"],
                       "character":actors[0]["character"],"object_id":oi,
                       "object":prop(oi),"duration_seconds":2.0})
    return {"seed":seed,"scene_count":len(scenes),"scenes":scenes,
            "story_subjects_verified":True,"ensemble_enabled":True,
            "publication_allowed":False,"quality_approved":False}


def verify_story_cast(plan):
    """Reject visual cast mismatches rather than silently substituting."""
    established_cast = {}
    for scene in plan["scenes"]:
        if plan.get("ensemble_enabled") and not scene.get("actors"):
            raise ValueError(f"scene {scene['scene']}: ensemble cast missing")
        if plan.get("story_subjects_verified") and not scene.get("subject"):
            raise ValueError(f"scene {scene['scene']}: verified story subject missing")
        subject = scene.get("subject")
        if not subject or character(scene["character_id"])[0] != subject:
            raise ValueError(f"scene {scene['scene']}: subject/cast mismatch")
        actors = scene.get("actors", [])
        if actors and (scene["character_id"] != actors[0]["character_id"] or subject != actors[0]["subject"]):
            raise ValueError(f"scene {scene['scene']}: primary actor mismatch")
        if len(actors) != len({actor["subject"] for actor in actors}):
            raise ValueError(f"scene {scene['scene']}: duplicate ensemble actor")
        for actor in actors:
            if character(actor["character_id"])[0] != actor["subject"]:
                raise ValueError(f"scene {scene['scene']}: ensemble actor mismatch")
            previous = established_cast.setdefault(actor["subject"], actor["character_id"])
            if previous != actor["character_id"]:
                raise ValueError(f"scene {scene['scene']}: actor identity changed")
    return True


def build_comedy_demo(seed="astra-comedy-pilot"):
    """One coherent offline comedy beat, not random unrelated catalog scenes.

    A fox tries to carry a gift, a rabbit reacts, and the fox celebrates.
    Keep the same actors and prop across all five shots.
    """
    plan = build_ensemble_plan(seed, [
        ["fox", "rabbit"], ["fox", "rabbit"], ["fox", "rabbit"],
        ["fox", "rabbit"], ["fox", "rabbit"],
    ])
    actions = ("approach", "point", "carry", "react", "celebrate")
    narrations = (
        "A fox spots a mystery gift.",
        "The rabbit points at the suspicious box.",
        "The fox grabs it before thinking.",
        "The rabbit freezes in disbelief.",
        "The fox celebrates like it won a trophy.",
    )
    # Gift category is index 38 of the 40-category prop catalog.
    for scene, action, narration in zip(plan["scenes"], actions, narrations):
        scene["object_id"] = 1900
        scene["object"] = prop(1900)
        scene["action"] = action
        scene["narration"] = narration
        scene["duration_seconds"] = 2.0
        # Opt-in illustrated actors on the isolated pilot only.
        scene["visual_style"] = "storybook"
    plan["pilot_type"] = "offline_comedy"
    plan["publication_allowed"] = False
    plan["quality_approved"] = False
    verify_story_cast(plan)
    return plan


def carry_shoulder_anchor(index, t, x, y, side, storybook=False):
    """Return the exact shoulder joint of the selected character renderer."""
    if storybook:
        return storybook_shoulder_anchor(index, t, x, y, side)
    if getattr(draw_character, "__name__", "") == "draw_character_silhouette":
        return (x + side * 58, y + int(12 * math.sin(t * 2.5 + index * .031)) + 55)
    return (x + side * 85, y + int(14 * math.sin(t * 2.2)) + 90)


def carry_elbow(shoulder, hand, side, scale=1.0):
    """Two-bone 2D elbow whose forearm endpoint matches the moving prop.

    A narrow elbow bend prevents the exaggerated diamond-shaped reach.
    Segments remain connected to the gift throughout the lift.
    """
    dx, dy = hand[0] - shoulder[0], hand[1] - shoulder[1]
    distance = max(0.001, math.hypot(dx, dy))
    height = max(16.0 * scale, min(44.0 * scale, distance * 0.13))
    midpoint = (shoulder[0] + dx / 2, shoulder[1] + dy / 2)
    elbow = (midpoint[0] + side * dy / distance * height,
             midpoint[1] - side * dx / distance * height)
    return elbow


def draw_expressive_character(image, index, t, x, y, expression, gesture="idle"):
    """Use full authored poses, falling back only for legacy test renderers."""
    try:
        return draw_character(image, index, t, x, y,
                              expression=expression, gesture=gesture)
    except TypeError as exc:
        if "unexpected keyword argument 'gesture'" in str(exc):
            return draw_character(image, index, t, x, y, expression=expression)
        if "unexpected keyword argument 'expression'" in str(exc):
            return draw_character(image, index, t, x, y)
        raise


def render_scene_actor(image, index, t, x, y, expression, gesture, storybook=False):
    if storybook and character(index)[0] in ("fox", "rabbit"):
        return draw_storybook_character(image, index, t, x, y,
                                        expression=expression, gesture=gesture)
    return draw_expressive_character(image, index, t, x, y, expression, gesture)


def frame(scene, t):
    """Experimental scene composition with depth, a shared stage and interaction."""
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    number = scene["scene"]
    theme = ((29, 48, 75), (48, 42, 73), (34, 67, 68), (72, 48, 58))[number % 4]
    # Location-specific palettes are opt-in for offline story rehearsals.
    # Keep the established comedy pilot's original palette unchanged.
    locations = {
        "bakery": ((97, 62, 65), (120, 84, 68)),
        "workshop": ((37, 65, 91), (67, 92, 109)),
        "park": ((34, 83, 71), (67, 112, 82)),
        "observatory": ((32, 34, 85), (59, 49, 108)),
    }
    if scene.get("location") in locations:
        theme = locations[scene["location"]][number % 2]
    # Layered atmospheric backdrop and parallax silhouettes.
    for y in range(H):
        mix = y / H
        shade = tuple(int(theme[c] * (1 - mix * 0.55) + BG[c] * mix * 0.55) for c in range(3))
        d.line((0, y, W, y), fill=shade)
    drift = int(12 * math.sin(t * 0.7 + number) + 8 * math.sin(t * 0.35))
    for i in range(7):
        xx = (i * 101 + number * 47 + drift) % (W + 110) - 55
        yy = 125 + (i * 83 + number * 19) % 360
        rr = 16 + i % 3 * 13
        d.ellipse((xx-rr, yy-rr, xx+rr, yy+rr), outline=(84, 104, 132), width=2)
    # Distinct depth layers and lighting give the comedy stage more structure.
    light_x = 105 + (number % 3) * 155 + int(14 * math.sin(t * 0.6))
    d.ellipse((light_x - 100, 60, light_x + 100, 270), fill=(58, 75, 96))
    for k in range(4):
        x = (k * 153 + 47 + drift // 2) % (W + 90) - 45
        d.polygon([(x - 28, 635), (x, 435 + 23 * (k % 2)), (x + 29, 635)], fill=(27, 49, 62))
    # Stage shared by both actors, rather than two disconnected panels.
    d.ellipse((-160, 575, 710, 940), fill=(28, 43, 61))
    d.ellipse((45, 710, 495, 785), fill=(22, 31, 45))
    d.line((0, 772, W, 772), fill=(97, 119, 138), width=4)
    # Draw on transparent layers to avoid hiding the background.
    character_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    object_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    actions = {"approach": 0, "react": 1, "point": 2, "celebrate": 3, "carry": 4,
               "walk": 5, "run": 6, "jump": 7, "dance": 8}
    named_action = scene.get("action")
    if named_action is not None and named_action not in actions:
        raise ValueError(f"scene {number}: unsupported action {named_action!r}")
    action = actions[named_action] if named_action is not None else number % 4
    # Explicit actions are authored stage cues, not inferred narration.
    progress = max(0.0, min(1.0, t / 2.2))
    approach = progress * progress * (3.0 - 2.0 * progress)
    cx = 310 + int(38 * approach) if action in (0, 2) else 320
    ox = 760 - int(50 * approach) if action in (0, 2) else 745
    cy = 1060 + int(13 * math.sin(t * 2.4))
    oy = 1180 + int(15 * math.sin(t * 2.1 + 1.0))
    actors = scene.get("actors")
    storybook = scene.get("visual_style") == "storybook"
    # The gift remains in the fox's paws after pickup, including reactions
    # and the trophy-like ending; no teleport back to the stage floor.
    held_action = named_action == "carry" or (storybook and named_action in ("react", "celebrate"))
    carry_shift = int(28 * math.sin(t * 2.0)) if named_action == "carry" else 0
    # The prop is lifted during the carry beat, rather than teleporting to the hands.
    lift_progress = max(0.0, min(1.0, (t - 0.15) / 0.95))
    lift_progress = lift_progress * lift_progress * (3.0 - 2.0 * lift_progress)
    if storybook and named_action in ("react", "celebrate"):
        lift_progress = 1.0
    lead_sway = 0
    lead_shoulders = None
    lead_base = None
    if actors:
        # Keep every actor on the same stage, with stable left-to-right slots.
        # Render each actor onto its own transparent layer before compositing.
        count = len(actors)
        slots = ([540], [290, 790], [210, 540, 870],
                 [155, 410, 670, 925])[count - 1]
        # Scale complete actor layers to their available stage width. The
        # character renderer has a fixed native footprint, so merely changing
        # center coordinates does not prevent crowding.
        scale = (1.0, 0.82, 0.66, 0.53)[count - 1]
        for actor_index, (actor, slot) in enumerate(zip(actors, slots)):
            actor_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            # Distinct, deterministic actor timing: ensemble members do not
            # all blink/bob in lockstep. The lead moves towards the prop on
            # approach and points toward it on the authored point cue.
            phase = actor_index * 0.43 + (actor["character_id"] % 7) * 0.11
            sway = int(9 * math.sin(t * 2.0 + slot / 180 + phase))
            if named_action == 'carry' and actor_index == 1:
                sway += int(14 * max(0.0, math.sin((t - 0.35) * 3.1)))
            if named_action == 'celebrate' and actor_index == 0:
                # Anticipation, bounce and settle: a damped oscillation avoids
                # perpetual mechanical shaking in the final hero pose.
                elapsed = max(0.0, t - 0.12)
                sway += int(18 * math.exp(-1.35 * elapsed) *
                            math.sin(9.0 * elapsed))
            actor_t = t + phase
            # Opt-in locomotion for experimental story batches only.
            # Lead and supporting actor use different phase offsets.
            if named_action in ("walk", "run", "jump", "dance"):
                speed = {"walk": 2.7, "run": 6.3, "jump": 4.0, "dance": 5.2}[named_action]
                stride = math.sin(t * speed + phase)
                if named_action == "walk":
                    sway += int(23 * math.sin(min(t, 1.8) / 1.8 * math.pi / 2))
                    sway += int(5 * stride)
                elif named_action == "run":
                    sway += int(44 * math.sin(min(t, 1.8) / 1.8 * math.pi / 2))
                    sway += int(12 * stride)
                elif named_action == "jump":
                    # Vertical displacement applied to the complete actor layer.
                    actor_t += 0.18
                else:
                    sway += int(24 * stride)
            if named_action == "approach":
                sway += int((22 if actor_index == 0 else 8) * approach)
            elif named_action == "react":
                # Brief recoil followed by a settled hold for readability.
                recoil = max(0.0, t - 0.18)
                sway += int(16 * math.exp(-2.0 * recoil) *
                            math.sin(8.0 * recoil + phase))
            elif named_action == "celebrate":
                sway += int(12 * math.sin(t * 4.0 + phase))
            if actor_index == 0:
                lead_sway = sway
            # Actor-specific comedy blocking: the rabbit reacts to the fox
            # instead of mirroring the fox's expression in every shot.
            if actor_index == 0:
                expression = ("surprised" if named_action == "react" else
                              "happy" if named_action == "celebrate" else
                              "focused" if named_action in ("point", "carry") else
                              "neutral")
                gesture = ("carry_rig" if held_action else
                           named_action if named_action in ("point", "celebrate") else "idle")
            else:
                expression = ("surprised" if named_action in ("carry", "react", "celebrate") else
                              "focused" if named_action == "point" else "neutral")
                gesture = "point" if named_action == "point" else "idle"
            render_scene_actor(actor_layer, actor["character_id"], actor_t, 540, 1060,
                               expression, gesture, storybook=storybook)
            if scale != 1.0:
                # Crop to actual visible artwork before scaling: resizing a
                # full-screen transparent canvas shrinks the character twice.
                bbox = actor_layer.getbbox()
                if bbox:
                    artwork = actor_layer.crop(bbox)
                    new_w = max(1, int(artwork.width * scale))
                    new_h = max(1, int(artwork.height * scale))
                    scaled = artwork.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    actor_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                    crouch = int(155 * (1.0 - lift_progress)) if named_action == "carry" and actor_index == 0 else 0
                    place_x = int(slot + sway + (carry_shift if actor_index == 0 else 0) - new_w / 2)
                    jump_offset = int(95 * max(0.0, math.sin(t * 3.4 + phase))) if named_action == "jump" else 0
                    dance_offset = int(22 * math.sin(t * 5.2 + phase)) if named_action == "dance" else 0
                    place_y = int(cy + crouch - new_h / 2 - jump_offset + dance_offset)
                    if held_action and actor_index == 0:
                        native_shoulders = tuple(carry_shoulder_anchor(
                            actor["character_id"], actor_t, 540, 1060, side,
                            storybook=storybook)
                            for side in (-1, 1))
                        lead_shoulders = tuple((
                            place_x + (point[0] - bbox[0]) * scale,
                            place_y + (point[1] - bbox[1]) * scale,
                        ) for point in native_shoulders)
                        # The original actor layer has already been replaced
                        # with a blank compositing canvas. Sample color from
                        # the preserved, unscaled cropped artwork instead.
                        lead_base = ((240, 120, 62) if storybook else artwork.getpixel((
                            int(540 - bbox[0]),
                            int(native_shoulders[0][1] + 40 - bbox[1])))[:3])
                    actor_layer.alpha_composite(scaled, (place_x, place_y))
            if scale == 1.0:
                # The solo ensemble actor must receive the same authored
                # lateral motion as scaled ensemble members.
                shifted = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                crouch = int(155 * (1.0 - lift_progress)) if named_action == "carry" and actor_index == 0 else 0
                shifted.alpha_composite(actor_layer,
                                        (sway + (carry_shift if actor_index == 0 else 0), crouch))
                actor_layer = shifted
                if held_action and actor_index == 0:
                    native_shoulders = tuple(carry_shoulder_anchor(
                        actor["character_id"], actor_t, 540, 1060, side,
                        storybook=storybook)
                        for side in (-1, 1))
                    lead_shoulders = tuple((
                        point[0] + sway + carry_shift, point[1] + crouch
                    ) for point in native_shoulders)
                    lead_base = ((240, 120, 62) if storybook else actor_layer.getpixel((
                        int(540 + sway + carry_shift),
                        min(1919, int(native_shoulders[0][1] + 40 + crouch))))[:3])
            character_layer = Image.alpha_composite(character_layer, actor_layer)
        # Move the prop forward so it does not cover the ensemble.
        ox, oy = 540, 1510
    else:
        expression = ("surprised" if named_action == "react" else
                      "happy" if named_action == "celebrate" else
                      "focused" if named_action in ("point", "carry") else "neutral")
        render_scene_actor(character_layer, scene["character_id"], t,
                           cx + carry_shift, cy, expression,
                           "carry_rig" if held_action else
                           named_action if named_action in ("point", "celebrate") else "idle",
                           storybook=storybook)
        if held_action:
            lead_shoulders = tuple(carry_shoulder_anchor(
                scene["character_id"], t, cx + carry_shift, cy, side,
                storybook=storybook)
                for side in (-1, 1))
            lead_base = ((240, 120, 62) if storybook else character_layer.getpixel((
                cx + carry_shift, min(1919, int(lead_shoulders[0][1] + 40))))[:3])
    if held_action:
        # Stage the object next to the lead actor, moving in sync with them.
        # This is a simple composited carry cue, not inverse-kinematic gripping.
        lead_x = (slots[0] if actors else cx)
        # Carry the object between the two lowered hands, not beside the
        # character's torso. For ensemble scenes, match the lead's scale and
        # its deterministic sway. This remains a 2D staged interaction.
        lead_scale = (1.0, 0.82, 0.66, 0.53)[len(actors) - 1] if actors else 1.0
        ox = int(sum(point[0] for point in lead_shoulders) / 2) if lead_shoulders else lead_x + carry_shift + lead_sway
        floor_y = 1510
        # Anchor to the actual transformed shoulders, accounting for crop,
        # scaling, idle bob, crouching and lateral movement. This avoids
        # guessing the hand position from a global stage coordinate.
        anchor_y = int(sum(point[1] for point in lead_shoulders) / 2) if lead_shoulders else cy
        if storybook and named_action == "celebrate":
            # Stage the gift above and slightly right of the fox's head,
            # keeping facial acting visible instead of masking the face.
            hand_y = anchor_y - int(315 * lead_scale) - int(14 * math.sin(t * 5))
            ox += int(175 * lead_scale)
        else:
            hand_y = anchor_y + int(70 * lead_scale)
        oy = int(floor_y * (1.0 - lift_progress) + hand_y * lift_progress)
    if held_action:
        # Carry objects should remain visually subordinate to the actor.
        # Scale the visible prop footprint instead of shrinking its entire
        # transparent drawing canvas.
        native = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw_prop(native, scene["object_id"], t, 540, 960)
        bbox = native.getbbox()
        if bbox:
            artwork = native.crop(bbox)
            prop_scale = (0.72 if actors and len(actors) > 1 else 0.80) if storybook else (0.55 if actors and len(actors) > 1 else 0.72)
            prop_scale *= 0.92 + 0.08 * lift_progress
            # Keep the carried prop in front of the torso, but within arm reach.
            if lift_progress >= 0.999:
                assert abs(oy - hand_y) <= 1, 'carried prop missed hand anchor'
            else:
                # During pickup, the gift intentionally moves from floor to hand.
                assert min(floor_y, hand_y) - 1 <= oy <= max(floor_y, hand_y) + 1
            pw = max(1, int(artwork.width * prop_scale))
            ph = max(1, int(artwork.height * prop_scale))
            artwork = artwork.resize((pw, ph), Image.Resampling.LANCZOS)
            object_layer.alpha_composite(artwork, (int(ox - pw / 2), int(oy - ph / 2)))
            if storybook and named_action == "celebrate":
                draw_gift_surprise(object_layer, ox, oy, pw, ph, t)
            if lead_shoulders is not None:
                # Anatomically linked two-segment arms extend from the
                # character's transformed shoulders to the exact prop sides.
                # They render behind the prop; small palms cover its edges.
                arm_draw = ImageDraw.Draw(character_layer)
                hand_draw = ImageDraw.Draw(object_layer)
                arm_width = max(10, int(20 * lead_scale))
                palm_radius = max(7, int(13 * lead_scale))
                for index, side in enumerate((-1, 1)):
                    shoulder = lead_shoulders[index]
                    hand = (ox + side * pw * 0.46, oy + ph * 0.07)
                    elbow = carry_elbow(shoulder, hand, side, lead_scale)
                    arm_draw.line((shoulder, elbow, hand),
                                  fill=(42, 49, 61, 255), width=arm_width + 6, joint="curve")
                    arm_draw.line((shoulder, elbow, hand),
                                  fill=(*lead_base, 255), width=arm_width, joint="curve")
                    arm_draw.ellipse((elbow[0] - arm_width / 2, elbow[1] - arm_width / 2,
                                      elbow[0] + arm_width / 2, elbow[1] + arm_width / 2),
                                     fill=(*lead_base, 255))
                    hand_draw.ellipse((hand[0] - palm_radius, hand[1] - palm_radius,
                                       hand[0] + palm_radius, hand[1] + palm_radius),
                                      fill=(*lead_base, 255))
                    hand_draw.line((hand[0], hand[1] + palm_radius / 3,
                                    hand[0] - side * palm_radius * 0.6,
                                    hand[1] + palm_radius * 0.9),
                                   fill=(*lead_base, 255), width=max(4, int(7 * lead_scale)))
    else:
        draw_prop(object_layer, scene["object_id"], t, ox, oy)
    if storybook and named_action == "celebrate":
        # Draw deterministic trophy glints on the same object layer so they
        # follow the camera's crop/zoom along with the carried gift.
        glints = ImageDraw.Draw(object_layer)
        for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2,
                      math.pi / 4, 3 * math.pi / 4):
            radius = 98 + int(9 * math.sin(t * 5 + angle))
            gx = ox + math.cos(angle) * radius
            gy = oy + math.sin(angle) * radius
            arm = 12 + 4 * (math.sin(t * 4 + angle) ** 2)
            glints.line((gx - arm, gy, gx + arm, gy),
                        fill=(253, 219, 117, 245), width=6)
            glints.line((gx, gy - arm, gx, gy + arm),
                        fill=(253, 219, 117, 245), width=6)
    # Frame-specific framing: wide setup, tighter reaction, and hero finale.
    # Transform the character and prop together to preserve contact alignment.
    if actors and named_action in ('point', 'react', 'celebrate'):
        zoom = {'point': 1.05, 'react': 1.11, 'celebrate': 1.08}[named_action]
        def framed(layer):
            nw, nh = int(1080 * zoom), int(1920 * zoom)
            enlarged = layer.resize((nw, nh), Image.Resampling.BICUBIC)
            xoff = (nw - 1080) // 2
            yoff = (nh - 1920) // 2
            return enlarged.crop((xoff, yoff, xoff + 1080, yoff + 1920))
        character_layer = framed(character_layer)
        object_layer = framed(object_layer)
    image = Image.alpha_composite(image.convert("RGBA"), character_layer.resize((W, H), Image.Resampling.LANCZOS))
    image = Image.alpha_composite(image, object_layer.resize((W, H), Image.Resampling.LANCZOS))
    d = ImageDraw.Draw(image)
    # Remove detached debugging-style interaction marks (yellow ring,
    # yellow diagonal stroke, cyan arc). These marks did not track the
    # characters or props and read as rendering artifacts. Physical
    # acting, props, camera motion and audio cues remain unchanged.
    if storybook and named_action in ("approach", "point", "carry", "react", "celebrate"):
        image = camera_frame(image.convert("RGB"), named_action, min(3., t))
        d = ImageDraw.Draw(image)
    if named_action and scene.get('actors'):
        cue = ('HONK?!' if storybook and named_action == 'celebrate' and t >= 1.65 else
               {'approach': 'WHAT IS THAT?', 'point': 'DONT TOUCH IT!',
                'carry': 'TOO LATE...', 'react': 'OH NO!',
                'celebrate': 'I DID IT!', 'walk': 'ON MY WAY!',
                'run': 'HURRY!', 'jump': 'UP WE GO!',
                'dance': 'LET US DANCE!'}[named_action])
        if storybook:
            if named_action in ("approach", "point", "carry", "react", "celebrate"):
                draw_caption(image, named_action, t, storybook=True)
            else:
                d.rounded_rectangle((85, 100, W-85, 158), radius=16, fill=(19, 30, 48, 230))
                d.text((W // 2 - 4 * len(cue), 122), cue, fill=(255, 228, 169))
        else:
            d.rounded_rectangle((80, 105, W-80, 157), radius=18, fill=(19, 30, 48, 230))
            d.text((W // 2 - 4 * len(cue), 124), cue, fill=(255, 228, 169))
    # Offline authored captions, timed to each scene and never used as speech.
    if scene.get("pilot_type") == "offline_story_batch" or (
        scene.get("visual_style") == "storybook" and scene.get("caption")
    ):
        words = str(scene.get("caption", "")).strip()
        if words:
            import textwrap
            caption_lines = textwrap.wrap(words, width=35)[:3]
            d.rounded_rectangle((32, 794, W-32, 875), radius=16,
                                fill=(15, 23, 39))
            for line_index, line in enumerate(caption_lines):
                d.text((48, 804 + 22 * line_index), line,
                       fill=(250, 242, 213))
    d.rounded_rectangle((18, 20, W-18, 65), radius=14, fill=(18, 26, 40, 255))
    d.text((30, 35), f"SCENE {number:02d}  /  ASTRA EXPERIMENT", fill=(239, 239, 228))
    d.text((24, 925), "NOT APPROVED FOR PUBLICATION", fill=(245, 176, 121))
    return image.convert("RGB")

def render(plan, output, fps=8, seconds_per_scene=2, video=False):
    if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list):
        raise ValueError("invalid scene plan")
    for scene in plan["scenes"]:
        if scene.get("action") is not None and scene["action"] not in (
            "approach", "react", "point", "celebrate", "carry",
            "walk", "run", "jump", "dance"
        ):
            raise ValueError(f"scene {scene.get('scene')}: unsupported action")
    if plan.get("ensemble_enabled") or plan.get("story_subjects_verified") or any(
        "subject" in scene or "actors" in scene for scene in plan["scenes"]
    ):
        verify_story_cast(plan)
    if not 2 <= fps <= 24 or not 1 <= seconds_per_scene <= 10:
        raise ValueError("fps or duration outside safe range")
    output.mkdir(parents=True, exist_ok=True)
    previews = []
    motion_failures = []
    scene_fingerprints = []
    visual_collisions = []
    seen_cast_pairs = set()
    for scene in plan["scenes"]:
        first, later = frame(scene, 0.0), frame(scene, 0.75)
        if ImageChops.difference(first, later).getbbox() is None:
            motion_failures.append(scene["scene"])
        # Frame fingerprints catch visually identical scene openings despite
        # different catalog identifiers. This is not semantic quality scoring.
        # Exclude scene labels: different scene numbers must not disguise
        # identical artwork. Compare only the two artwork regions.
        artwork_only = Image.new("RGB", (W, 860), BG)
        artwork_only.paste(first.crop((0, 80, W, 550)), (0, 0))
        artwork_only.paste(first.crop((0, 570, W, 870)), (0, 500))
        fingerprint = hashlib.sha256(artwork_only.resize((108, 172)).tobytes()).hexdigest()
        # Background changes must not disguise a repeated cast/prop pairing.
        # Keep both the semantic pairing gate and pixel-level scene gate.
        pair = (scene["character_id"], scene["object_id"])
        # Story-led scenes may intentionally reuse the same protagonist and
        # prop. Their actual artwork must still change. Random catalog demos
        # retain the stricter repeated-pair rejection.
        repeated_pair = pair in seen_cast_pairs
        repeated_artwork = fingerprint in scene_fingerprints
        if repeated_artwork or (repeated_pair and not plan.get("story_subjects_verified")):
            visual_collisions.append(scene["scene"])
        seen_cast_pairs.add(pair)
        scene_fingerprints.append(fingerprint)
        if len(previews) < 12:
            # Show the completed interaction, not only the floor-level first
            # frame. Motion validation and scene fingerprints still use first.
            preview_frame = frame(scene, min(seconds_per_scene - 0.1, 1.4)) if scene.get('action') == 'carry' else first
            previews.append(preview_frame.resize((270, 480)))
    sheet = Image.new("RGB", (270 * 4, 480 * math.ceil(len(previews) / 4)), BG)
    for i, image in enumerate(previews):
        sheet.paste(image, ((i % 4) * 270, (i // 4) * 480))
    sheet.save(output / "storyboard.png")
    if plan.get("pilot_type") == "offline_comedy":
        # Early vs late frames reveal the camera move and duck-in-box finale.
        beat_sheet = Image.new("RGB", (270 * len(plan["scenes"]), 960), BG)
        for i, scene in enumerate(plan["scenes"]):
            for row, sample in enumerate((0.6, min(seconds_per_scene - .1, 2.3))):
                beat_sheet.paste(frame(scene, sample).resize((270, 480)),
                                 (i * 270, row * 480))
        beat_sheet.save(output / "cinematic-beats.png")
    # Explicit contact-sheet evidence across the pickup arc, so a successful
    # first-frame storyboard cannot mask a failed or incomplete interaction.
    carry_scenes = [s for s in plan["scenes"] if s.get("action") == "carry"]
    if carry_scenes:
        samples = [0.0, 0.35, 0.7, 1.1, min(seconds_per_scene - 0.1, 1.8)]
        pickup_sheet = Image.new("RGB", (270 * len(samples), 480 * len(carry_scenes)), BG)
        for row, carry_scene in enumerate(carry_scenes):
            for column, sample in enumerate(samples):
                pickup_sheet.paste(frame(carry_scene, max(0.0, sample)).resize((270, 480)),
                                   (column * 270, row * 480))
        pickup_sheet.save(output / "pickup-motion-sheet.png")
    report = {
        "scene_count": len(plan["scenes"]),
        "unique_characters": len({actor["character_id"] for s in plan["scenes"] for actor in (s.get("actors") or [{"character_id": s["character_id"]}])}),
        "unique_objects": len({s["object_id"] for s in plan["scenes"]}),
        "motion_failures": motion_failures,
        "visually_duplicate_scene_openings": visual_collisions,
        "unique_scene_frame_fingerprints": len(set(scene_fingerprints)),
        "publication_allowed": False,
        "quality_approved": False,
        "cinematic_camera": plan.get("pilot_type") == "offline_comedy",
        "duck_surprise": plan.get("pilot_type") == "offline_comedy",
        "scene_dissolves": plan.get("pilot_type") == "offline_comedy",
        "note": "Offline technical candidate; manual creative review required.",
    }
    if video:
        import imageio_ffmpeg
        encoder = imageio_ffmpeg.write_frames(
            str(output / "preview.mp4"), (W, H), fps=fps,
            codec="libx264", output_params=["-pix_fmt", "yuv420p", "-crf", "27"],
        )
        encoder.send(None)
        try:
            for i, scene in enumerate(plan["scenes"]):
                prev = (frame(plan["scenes"][i - 1], seconds_per_scene - 1 / fps)
                        if i and plan.get("pilot_type") == "offline_comedy" else None)
                for k in range(fps * seconds_per_scene):
                    local = k / fps
                    current = frame(scene, local)
                    if prev is not None and local < .25:
                        current = dissolve(prev, current, local)
                    encoder.send(current.tobytes())
        finally:
            encoder.close()
        if plan.get("pilot_type") == "offline_comedy":
            from astra_v2.comedy_sound import write_soundtrack
            sound_report = write_soundtrack(
                plan, output / "soundtrack.wav", seconds_per_scene=seconds_per_scene,
            )
            source_mp4 = output / "preview.mp4"
            multiplexed_mp4 = output / "preview-with-sound.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source_mp4), "-i", str(output / "soundtrack.wav"),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-ar", "24000", "-ac", "1", "-movflags", "+faststart",
                "-t", str(len(plan["scenes"]) * seconds_per_scene),
                str(multiplexed_mp4),
            ], check=True, timeout=90)
            audio_streams = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,codec_name", "-of", "json",
                str(multiplexed_mp4),
            ], timeout=20))["streams"]
            if not any(s.get("codec_type") == "audio" and
                       s.get("codec_name") == "aac" for s in audio_streams):
                raise RuntimeError("the comedy pilot is missing AAC audio")
            multiplexed_mp4.replace(source_mp4)
            report["audio_codec"] = "aac"
            report["audio_origin"] = sound_report["origin"]
            report["original_audio_cues"] = sound_report["cue_count"]
    (output / "plan.json").write_text(json.dumps(plan, indent=2))
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if motion_failures or visual_collisions:
        raise RuntimeError(f"Preview quality gate failed: motion={motion_failures}, duplicate_openings={visual_collisions}")
    return report



def load_story_file(path, seed):
    """Load explicitly authored offline scene casts; never infer or publish."""
    path = Path(path)
    if path.stat().st_size > 100_000:
        raise ValueError("story file exceeds 100 KB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"mode", "scenes"}:
        raise ValueError("story file requires only mode and scenes")
    scenes = data["scenes"]
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 24:
        raise ValueError("story requires 1..24 scenes")
    mode = data["mode"]
    if mode == "ensemble":
        if any(not isinstance(item, dict) or set(item) - {"actors", "action", "narration", "object_id"}
               or "actors" not in item for item in scenes):
            raise ValueError("ensemble scenes require actors, optional action/narration")
        for item in scenes:
            actors = item["actors"]
            if not isinstance(actors, list) or not 1 <= len(actors) <= 4 or any(
                not isinstance(actor, str) for actor in actors
            ):
                raise ValueError("ensemble actors must be a list of 1..4 species names")
        plan = build_ensemble_plan(seed, [item["actors"] for item in scenes])
    elif mode == "narrated":
        if any(not isinstance(item, dict) or set(item) != {"narration"} or
               not isinstance(item["narration"], str) for item in scenes):
            raise ValueError("narrated scenes require narration strings")
        plan = build_narrated_plan(seed, [item["narration"] for item in scenes])
    else:
        raise ValueError("unsupported story mode")
    # A recurring story prop must keep its exact catalog identity across
    # scenes. Explicit object_id is allowed; otherwise inherit scene one's
    # prop instead of silently randomizing it every scene.
    if mode == "ensemble":
        shared_object = scenes[0].get("object_id", plan["scenes"][0]["object_id"])
        if type(shared_object) is not int or not 0 <= shared_object < 2000:
            raise ValueError("object_id must be an integer from 0 to 1999")
        for scene, item in zip(plan["scenes"], scenes):
            object_id = item.get("object_id", shared_object)
            if type(object_id) is not int or not 0 <= object_id < 2000:
                raise ValueError("object_id must be an integer from 0 to 1999")
            from astra_v2.character_object_catalog import prop
            scene["object_id"] = object_id
            scene["object"] = prop(object_id)
    for scene, item in zip(plan["scenes"], scenes):
        narration = item.get("narration")
        if narration is not None:
            if not isinstance(narration, str) or len(narration) > 1000:
                raise ValueError("narration must be text under 1000 characters")
            scene["narration"] = narration
        if "action" in item:
            if item["action"] not in ("approach", "react", "point", "celebrate", "carry"):
                raise ValueError("unsupported scene action")
            scene["action"] = item["action"]
    if not verify_story_cast(plan):
        raise ValueError("story cast verification failed")
    # A narrated ensemble requires explicit cast references for every named
    # supported species. This is lexical validation, not semantic parsing.
    if mode == "ensemble":
        from astra_v2.character_object_catalog import SPECIES
        import re
        for index, (scene, item) in enumerate(zip(plan["scenes"], scenes), 1):
            narration = item.get("narration", "")
            if not narration:
                continue
            words = set(re.findall(r"[a-z]+", narration.lower()))
            mentioned = {species for species in SPECIES if species in words}
            cast = {actor["subject"] for actor in scene["actors"]}
            if mentioned - cast:
                raise ValueError(
                    f"scene {index}: narration mentions species absent from cast: "
                    f"{sorted(mentioned - cast)}"
                )
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="astra-development-v1")
    parser.add_argument("--scenes", type=int, default=12)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--seconds-per-scene", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("development-output"))
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--comedy-pilot", action="store_true",
                        help="Render the fixed offline fox/rabbit comedy pilot")
    parser.add_argument("--story-file", type=Path, help="Explicit offline story JSON")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.comedy_pilot and args.story_file:
        parser.error("--comedy-pilot and --story-file are mutually exclusive")
    plan = (build_comedy_demo(args.seed) if args.comedy_pilot else
            load_story_file(args.story_file, args.seed) if args.story_file else
            build_plan(args.seed, args.scenes))
    if args.validate_only:
        print(json.dumps({"valid": True, "scene_count": len(plan["scenes"]),
                          "publication_allowed": False, "quality_approved": False}, indent=2))
    else:
        print(json.dumps(render(plan, args.output, fps=args.fps, seconds_per_scene=args.seconds_per_scene, video=args.video), indent=2))


if __name__ == "__main__":
    main()
