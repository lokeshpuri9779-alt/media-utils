"""Offline procedural animation library: 2000 indexed visual variants.

Twenty shapes, ten movement styles and ten palettes.
These are combinations, not 2000 hand-drawn unique characters.
"""
import math
from PIL import ImageDraw

SHAPES = ("spark", "bubble", "leaf", "star", "rain", "snow", "petal",
          "cloud", "planet", "comet", "confetti", "heart", "diamond",
          "ring", "wave", "gear", "bolt", "sun", "firefly", "balloon")
MOTIONS = ("float", "sway", "orbit", "bounce", "drift", "pulse", "spin",
           "fall", "rise", "zigzag")
COLORS = ((252,189,110), (119,205,234), (174,153,235), (135,217,160),
          (252,133,143), (255,220,130), (119,189,184), (202,166,138),
          (245,190,225), (207,218,241))
COUNT = len(SHAPES) * len(MOTIONS) * len(COLORS)

def variant(index):
    if not isinstance(index, int) or not 0 <= index < COUNT:
        raise ValueError("variant index out of range")
    return SHAPES[index // 100], MOTIONS[index // 10 % 10], COLORS[index % 10]

def draw(image, index, seconds, x=540, y=900, radius=40):
    shape, motion, color = variant(index)
    t = float(seconds)
    if motion == "float": y += int(35 * math.sin(t * 1.3))
    elif motion == "sway": x += int(48 * math.sin(t * 1.8))
    elif motion == "orbit":
        x += int(45 * math.cos(t * 1.5))
        y += int(45 * math.sin(t * 1.5))
    elif motion == "bounce": y -= int(60 * abs(math.sin(t * 2.4)))
    elif motion == "drift": x += int(65 * math.sin(t * 0.6))
    elif motion == "pulse": radius = int(radius * (1 + 0.16 * math.sin(t * 3)))
    elif motion == "spin":
        x += int(20 * math.sin(t * 3))
        y += int(20 * math.cos(t * 3))
    elif motion == "fall": y += int((t * 65) % 180) - 90
    elif motion == "rise": y -= int((t * 65) % 180) - 90
    elif motion == "zigzag":
        x += int(48 * math.sin(t * 4))
        y += int(17 * math.sin(t * 2))
    r = max(5, int(radius))
    d = ImageDraw.Draw(image)
    bounds = (x-r, y-r, x+r, y+r)
    if shape in ("bubble", "planet", "ring", "cloud"):
        d.ellipse(bounds, outline=color, width=max(2,r//5))
    elif shape in ("rain", "snow", "wave"):
        d.arc(bounds, 20, 170, fill=color, width=max(3,r//6))
    elif shape in ("leaf", "petal", "balloon", "heart"):
        d.ellipse(bounds, fill=color)
    elif shape in ("star", "spark", "comet", "confetti", "bolt", "firefly", "sun"):
        for k in range(8):
            a = k*math.pi/4 + (t*.5 if motion == "spin" else 0)
            d.line((x,y,x+int(r*math.cos(a)),y+int(r*math.sin(a))),
                   fill=color, width=4)
    else:
        d.polygon(((x,y-r),(x+r,y),(x,y+r),(x-r,y)),fill=color)
    return bounds
