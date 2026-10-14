"""Deterministic cinematic animation cues for the offline five-shot comedy.

No external media, API, paid dependency, or publication integration. All
geometry is deterministic so regressions can compare distinct visual beats.
"""
import math

from PIL import Image, ImageDraw


CAMERA_PRESETS = {
    "approach": (1.015, 1.075, -15, 10),
    "point": (1.13, 1.19, 13, -2),
    "carry": (1.035, 1.115, -6, 13),
    "react": (1.14, 1.235, 12, -18),
    "celebrate": (1.085, 1.17, -10, -18),
}

REVEAL_START = 1.4
REVEAL_DURATION = .55


def ease01(value):
    """Clamp and cubic-ease an interpolation fraction."""
    x = max(0., min(1., float(value)))
    return x * x * (3. - 2. * x)


def camera_params(action, t, seconds=3):
    """Return an action-specific zoom and safe pixel offsets."""
    if action not in CAMERA_PRESETS:
        raise ValueError("unsupported cinematic action")
    if not 0 <= t <= seconds or seconds <= 0:
        raise ValueError("camera local time outside scene")
    initial, final, dx, dy = CAMERA_PRESETS[action]
    factor = ease01(t / seconds)
    zoom = initial + (final - initial) * factor
    # Reactive camera has a brief eased impact without full-screen flashing.
    shake = math.sin((t - .36) * 24) * 2 * (1 - ease01((t - .36) / .65)) if (
        action == "react" and .36 <= t <= 1.01) else 0
    return zoom, dx * factor + shake, dy * factor


def camera_frame(image, action, t, seconds=3):
    """Move/zoom the finished artwork while leaving interface labels stable."""
    zoom, dx, dy = camera_params(action, t, seconds)
    width, height = image.size
    visible_w, visible_h = width / zoom, height / zoom
    # Bounded camera pan avoids black borders or implicit clip expansion.
    center_x = max(visible_w / 2, min(width - visible_w / 2,
                                      width * .5 + dx))
    center_y = max(visible_h / 2, min(height - visible_h / 2,
                                      height * .50 + dy))
    box = (center_x - visible_w / 2, center_y - visible_h / 2,
           center_x + visible_w / 2, center_y + visible_h / 2)
    return image.transform((width, height), Image.Transform.EXTENT, box,
                           resample=Image.Resampling.BICUBIC)


def draw_gift_surprise(layer, x, y, box_width, box_height, t):
    """Pop an original rubber-duck toy from the already-carried present.

    All inputs use native 1080x1920 character-stage coordinates. Nothing
    replaces the gift: the box remains in the fox's paws.
    """
    if t < REVEAL_START:
        return False
    fraction = ease01((t - REVEAL_START) / REVEAL_DURATION)
    if fraction <= 0:
        return False
    d = ImageDraw.Draw(layer, "RGBA")
    x = int(x)
    y = int(y)
    box_width = max(35, int(box_width))
    box_height = max(35, int(box_height))
    # Hinged lid opens up and to the left (this is a pop-up toy, not a
    # replacement asset). The spring terminates at the duck's body.
    lid_y = y - box_height * .46
    hinge_x = x - box_width * .43
    d.polygon((
        (hinge_x, lid_y),
        (hinge_x - 42 * fraction, lid_y - 60 * fraction),
        (x + box_width * .43 - 26 * fraction, lid_y - 81 * fraction),
        (x + box_width * .43, lid_y - 14 * fraction),
    ), fill=(168, 103, 63, 255), outline=(71, 52, 54, 255), width=5)
    height = 151 * fraction * (1 + .04 * math.sin(t * 15))
    body_y = lid_y - height
    # Visible compressed spring uncoils as the toy rises.
    previous = (x, lid_y)
    for i in range(1, 9):
        value = i / 8
        next_point = (x + (18 if i % 2 else -18) * fraction,
                      lid_y - height * value)
        d.line((previous, next_point), fill=(61, 71, 82, 255), width=7)
        previous = next_point
    radius = max(8, int(49 * fraction))
    body_x = x + int(10 * math.sin(t * 13) * fraction)
    d.ellipse((body_x - radius, body_y - int(radius * .60),
               body_x + radius, body_y + int(radius * 1.1)),
              fill=(252, 217, 79, 255), outline=(65, 54, 57, 255), width=6)
    # A small crest, oversized comic eyes, and an orange beak.
    for sign in (-1, 1):
        eye_x = body_x + sign * radius * .4
        eye_y = body_y - radius * .17
        eye_r = max(4, int(10 * fraction))
        d.ellipse((eye_x-eye_r, eye_y-eye_r, eye_x+eye_r, eye_y+eye_r),
                  fill=(255, 253, 239, 255), outline=(45, 48, 60, 255), width=3)
        pupil = max(2, int(4 * fraction))
        d.ellipse((eye_x-pupil+2, eye_y-pupil, eye_x+pupil+2, eye_y+pupil),
                  fill=(43, 45, 58, 255))
    beak_w = 27 * fraction
    beak_y = body_y + 12 * fraction
    d.polygon(((body_x-beak_w, beak_y),
               (body_x+beak_w, beak_y),
               (body_x, beak_y + 20 * fraction)),
              fill=(244, 143, 55, 255), outline=(83, 59, 54, 255), width=4)
    crest = 8 * fraction
    d.line(((body_x-crest, body_y-radius*.58),
            (body_x, body_y-radius*.9),
            (body_x+crest, body_y-radius*.6)),
           fill=(246, 175, 63, 255), width=max(2, int(6*fraction)))
    if t > REVEAL_START + .30:
        intensity = ease01((t - REVEAL_START - .30) / .32)
        for i in range(14):
            angle = 2 * math.pi * i / 14 + (i % 3) * .13
            dist = (72 + i % 4 * 14) * intensity
            px = body_x + math.cos(angle) * dist
            py = body_y + math.sin(angle) * dist
            size = 8 + i % 4 * 3
            shade = ((245, 167, 68, 255), (110, 205, 181, 255),
                     (255, 231, 142, 255), (230, 130, 162, 255))[i % 4]
            d.polygon(((px, py-size), (px+size*.9, py+size),
                       (px-size*.9, py+size*.45)), fill=shade)
    return True


def dissolve(previous, current, local_time, duration=.25):
    """Short scene change softened at the artwork level.

    The final result is always the current shot after the first 0.25 s.
    No frames are added or removed, so audio and visual beats remain aligned.
    """
    if previous is None or local_time >= duration:
        return current
    if previous.size != current.size:
        raise ValueError("transition requires matching frame dimensions")
    if local_time < 0:
        raise ValueError("scene time cannot be negative")
    alpha = ease01(local_time / duration)
    return Image.blend(previous.convert("RGB"), current.convert("RGB"), alpha)
