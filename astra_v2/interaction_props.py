"""CPU-safe foreground interaction props for existing ASTRA Pillow scenes.

Draw only when the action and narration explicitly support the prop.
Coordinates follow the existing 1080x1920 character focal area.
"""
import math
import re
from PIL import ImageDraw
from astra_v2.story_action_motion import offset


def prop_for_shot(shot):
    text = " ".join(str(shot.get(k) or "") for k in
                    ("visual_intent", "visual_prompt", "speech", "action")).lower()
    action = shot.get("story_action", "idle")
    if action in ("carry", "pick", "push", "pull") and re.search(
            r"\b(?:box|boxes|parcel|parcels|crate|crates|package|packages|cart|carts)\b", text):
        return "parcel"
    if re.search(r"\bnotebook\b", text):
        return "notebook"
    if action == "repair" and re.search(
            r"\b(?:tool|tools|hammer|wrench|repair|repairs|repaired|fix|fixes|fixed)\b", text):
        return "tool"
    return None


def draw_interaction_prop(image, shot, t):
    """Draw a prop near the moving character; return False when unsupported."""
    prop = prop_for_shot(shot)
    if prop is None:
        return False
    if not math.isfinite(t):
        raise ValueError("invalid interaction time")
    action = shot.get("story_action", "idle")
    dx, dy = offset(action, t)
    d = ImageDraw.Draw(image)
    if prop == "notebook":
        # A narrated notebook reveal must have a visible page, not only a
        # caption. Keep the open spread in the lower-left stage, clear of the
        # protagonist's face and the underwater doorway on the right.
        x, y = 235, 1035
        d.rounded_rectangle((x-118, y-112, x+118, y+112), radius=12,
                            fill=(82, 57, 48), outline=(224, 194, 145), width=8)
        d.polygon(((x, y-88), (x-102, y-78), (x-102, y+88), (x, y+74)),
                  fill=(246, 232, 194), outline=(126, 96, 70))
        d.polygon(((x, y-88), (x+102, y-78), (x+102, y+88), (x, y+74)),
                  fill=(238, 220, 178), outline=(126, 96, 70))
        # A miniature arched door makes the notebook's drawing legible as the
        # clue that connects the page to the submerged portal.
        d.arc((x-58, y-54, x-8, y+28), 180, 360, fill=(43, 94, 111), width=5)
        d.line((x-58, y-13, x-58, y+28), fill=(43, 94, 111), width=5)
        d.line((x-8, y-13, x-8, y+28), fill=(43, 94, 111), width=5)
        for yy in (y+42, y+55):
            d.line((x-74, yy, x-14, yy), fill=(157, 126, 91), width=3)
        d.line((x+22, y-35, x+78, y-35), fill=(157, 126, 91), width=4)
        d.line((x+22, y-17, x+78, y-17), fill=(157, 126, 91), width=4)
        d.line((x+22, y+1, x+68, y+1), fill=(157, 126, 91), width=4)
        return True
    if prop == "parcel":
        # Held parcels follow body motion; pushed/pulled parcels remain at ground.
        if action in ("push", "pull"):
            x, y = 745 + dx, 1050
        elif action == "pick":
            progress = max(0.0, min(1.0, t / 1.0))
            progress = progress * progress * (3.0 - 2.0 * progress)
            x, y = 665 + dx, round(1060 - 200 * progress)
        else:
            x, y = 665 + dx, 860 + dy
        d.rounded_rectangle((x-72, y-65, x+72, y+65),
                            radius=12, fill=(190, 137, 80),
                            outline=(70, 52, 40), width=7)
        d.line((x-72, y-10, x+72, y-10), fill=(236, 204, 142), width=9)
        d.line((x, y-65, x, y+65), fill=(236, 204, 142), width=9)
    else:
        # Repair tool follows the actor's gesture, not a separate random path.
        x = 650 + dx
        y = 900 + dy + round(14 * math.sin(t * 8))
        d.line((x, y-35, x+28, y+42), fill=(111, 77, 54), width=16)
        d.rounded_rectangle((x-36, y-48, x+44, y-20),
                            radius=6, fill=(115, 132, 148))
    return True
