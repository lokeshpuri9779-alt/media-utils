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


def frame(scene, t):
    """Experimental scene composition with depth, a shared stage and interaction."""
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    number = scene["scene"]
    theme = ((29, 48, 75), (48, 42, 73), (34, 67, 68), (72, 48, 58))[number % 4]
    # Layered atmospheric backdrop and parallax silhouettes.
    for y in range(H):
        mix = y / H
        shade = tuple(int(theme[c] * (1 - mix * 0.55) + BG[c] * mix * 0.55) for c in range(3))
        d.line((0, y, W, y), fill=shade)
    drift = int(12 * math.sin(t * 0.7 + number))
    for i in range(7):
        xx = (i * 101 + number * 47 + drift) % (W + 110) - 55
        yy = 125 + (i * 83 + number * 19) % 360
        rr = 16 + i % 3 * 13
        d.ellipse((xx-rr, yy-rr, xx+rr, yy+rr), outline=(84, 104, 132), width=2)
    # Stage shared by both actors, rather than two disconnected panels.
    d.ellipse((-160, 575, 710, 940), fill=(28, 43, 61))
    d.ellipse((45, 710, 495, 785), fill=(22, 31, 45))
    d.line((0, 772, W, 772), fill=(97, 119, 138), width=4)
    # Draw on transparent layers to avoid hiding the background.
    character_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    object_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    actions = {"approach": 0, "react": 1, "point": 2, "celebrate": 3}
    named_action = scene.get("action")
    if named_action is not None and named_action not in actions:
        raise ValueError(f"scene {number}: unsupported action {named_action!r}")
    action = actions[named_action] if named_action is not None else number % 4
    # Explicit actions are authored stage cues, not inferred narration.
    approach = math.sin(min(1.0, t / 1.4) * math.pi / 2)
    cx = 310 + int(38 * approach) if action in (0, 2) else 320
    ox = 760 - int(50 * approach) if action in (0, 2) else 745
    cy = 1060 + int(13 * math.sin(t * 2.4))
    oy = 1180 + int(15 * math.sin(t * 2.1 + 1.0))
    actors = scene.get("actors")
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
        for actor, slot in zip(actors, slots):
            actor_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            sway = int(9 * math.sin(t * 2.0 + slot / 180))
            draw_character(actor_layer, actor["character_id"], t, 540, 1060)
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
                    actor_layer.alpha_composite(scaled, (int(slot + sway - new_w / 2),
                                                        int(cy - new_h / 2)))
            # The solo actor keeps its original native composition.
            character_layer = Image.alpha_composite(character_layer, actor_layer)
        # Move the prop forward so it does not cover the ensemble.
        ox, oy = 540, 1510
    else:
        draw_character(character_layer, scene["character_id"], t, cx, cy)
    draw_prop(object_layer, scene["object_id"], t, ox, oy)
    image = Image.alpha_composite(image.convert("RGBA"), character_layer.resize((W, H), Image.Resampling.LANCZOS))
    image = Image.alpha_composite(image, object_layer.resize((W, H), Image.Resampling.LANCZOS))
    d = ImageDraw.Draw(image)
    # A visible cause/effect cue is a procedural interaction, not character acting.
    if action == 0:
        pulse = 13 + int(7 * (1 + math.sin(t * 3)))
        d.ellipse((374-pulse, 554-pulse, 374+pulse, 554+pulse),
                  outline=(250, 216, 127), width=4)
    elif action == 1:
        d.arc((295, 370, 480, 570), 190, 320, fill=(150, 215, 224), width=5)
    elif action == 2:
        d.line((290, 490, 400, 530), fill=(244, 199, 135), width=5)
    else:
        for j in range(3):
            d.ellipse((390+j*22, 440-j*23, 398+j*22, 448-j*23),
                      fill=(240, 205, 134))
    d.rounded_rectangle((18, 20, W-18, 65), radius=14, fill=(18, 26, 40, 255))
    d.text((30, 35), f"SCENE {number:02d}  /  ASTRA EXPERIMENT", fill=(239, 239, 228))
    d.text((24, 925), "NOT APPROVED FOR PUBLICATION", fill=(245, 176, 121))
    return image.convert("RGB")

def render(plan, output, fps=8, seconds_per_scene=2, video=False):
    if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list):
        raise ValueError("invalid scene plan")
    for scene in plan["scenes"]:
        if scene.get("action") is not None and scene["action"] not in (
            "approach", "react", "point", "celebrate"
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
        if pair in seen_cast_pairs or fingerprint in scene_fingerprints:
            visual_collisions.append(scene["scene"])
        seen_cast_pairs.add(pair)
        scene_fingerprints.append(fingerprint)
        if len(previews) < 12:
            previews.append(first.resize((270, 480)))
    sheet = Image.new("RGB", (270 * 4, 480 * math.ceil(len(previews) / 4)), BG)
    for i, image in enumerate(previews):
        sheet.paste(image, ((i % 4) * 270, (i // 4) * 480))
    sheet.save(output / "storyboard.png")
    report = {
        "scene_count": len(plan["scenes"]),
        "unique_characters": len({s["character_id"] for s in plan["scenes"]}),
        "unique_objects": len({s["object_id"] for s in plan["scenes"]}),
        "motion_failures": motion_failures,
        "visually_duplicate_scene_openings": visual_collisions,
        "unique_scene_frame_fingerprints": len(set(scene_fingerprints)),
        "publication_allowed": False,
        "quality_approved": False,
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
            for scene in plan["scenes"]:
                for k in range(fps * seconds_per_scene):
                    encoder.send(frame(scene, k / fps).tobytes())
        finally:
            encoder.close()
    (output / "plan.json").write_text(json.dumps(plan, indent=2))
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if motion_failures or visual_collisions:
        raise RuntimeError(f"Preview quality gate failed: motion={motion_failures}, duplicate_openings={visual_collisions}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="astra-development-v1")
    parser.add_argument("--scenes", type=int, default=12)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("development-output"))
    parser.add_argument("--video", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.seed, args.scenes)
    print(json.dumps(render(plan, args.output, fps=args.fps, video=args.video), indent=2))


if __name__ == "__main__":
    main()
