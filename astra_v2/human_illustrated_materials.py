"""Reusable, original hand-authored 2D scene and character material atlas.

These drawing recipes add distinct chapter-specific foreground *artwork*, not
post-processing or synthetic/stock imagery. They work with the existing
Pillow CPU renderer, preserve the verified background through the observatory
window, and reserve the upper/lower text-safe regions. The library is stable
across renders and never changes the production publishing configuration.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from astra_errors import CreativeReject

# Explicit directorial continuity: every authored story scene maps to a
# recognizably different location/lighting vocabulary, rather than all sixteen
# sharing an identical generic equipment/background treatment.
SET_PROFILES = {
    "discover_radio": "radio_workshop",
    "trace_cable": "radio_workshop",
    "hear_warning": "radio_workshop",
    "flee_door": "radio_workshop",
    "guard_knocking_door": "generator_bay",
    "inspect_generator_clue": "generator_bay",
    "inspect_future_photograph": "memory_archive",
    "stop_stranger_switch": "generator_bay",
    "survey_dead_city": "silent_city",
    "inspect_reverse_clock": "silent_city",
    "study_altered_photographs": "memory_archive",
    "confront_mara_double": "silent_city",
    "face_duplicate_at_countdown": "split_timelines",
    "warn_parallel_cities": "split_timelines",
    "split_glass_key": "split_timelines",
    "seal_and_reveal_sea_door": "ocean_chart",
}
MATERIALS = {
    "radio_workshop": {"accent":(89,195,188),"metal":(76,112,130),"light":(218,191,134)},
    "generator_bay": {"accent":(211,167,104),"metal":(92,111,129),"light":(121,204,171)},
    "memory_archive": {"accent":(186,151,201),"metal":(106,95,121),"light":(222,195,147)},
    "silent_city": {"accent":(113,162,213),"metal":(72,97,127),"light":(176,205,223)},
    "split_timelines": {"accent":(118,194,221),"metal":(111,105,150),"light":(237,203,145)},
    "ocean_chart": {"accent":(96,195,211),"metal":(81,128,157),"light":(209,224,186)},
}
SAFE_STAGE = (80,555,1000,1268)


def _require_frame(image, action, t, duration):
    if image.mode!="RGB" or image.size!=(1080,1920):
        raise CreativeReject("Material artwork expects RGB vertical Studio frame")
    if action not in SET_PROFILES:
        raise CreativeReject("No reviewed scenery artwork for " + str(action))
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (t,duration)):
        raise CreativeReject("Nonfinite environment artwork time")
    if t<0 or duration<=0:
        raise CreativeReject("Invalid environment artwork time")


def _stroke(draw, points, color, width=5):
    draw.line(points,fill=color,width=width,joint="curve")


def _workshop(d, profile, p):
    accent,metal,light=profile["accent"],profile["metal"],profile["light"]
    # Layered copper antenna/coaxial hardware mounted behind the story radio.
    for x in (208,270,333):
        d.line(((x,658),(x,849)),fill=metal,width=7)
        d.ellipse((x-11,672,x+11,694),fill=(33,49,68),outline=accent,width=4)
        d.arc((x-29,687,x+29,758),182,355,fill=light,width=3)
        for j in range(3):
            yy=778+j*22
            d.line(((x-15,yy),(x+15,yy)),fill=(143,160,165),width=3)
    d.polygon(((186,861),(356,861),(373,900),(188,900)),
              fill=(43,65,87),outline=(144,159,172),width=4)
    # Three concentric signal rings are subtle technical set dressing.
    for r in (17,38,61):
        d.arc((274-r,801-r,274+r,801+r),210,332,
              fill=accent if r<60 else metal,width=4)
    # Lamp intensity reflects the scene action's story progression.
    for i in range(5):
        x=770+i*37
        d.rounded_rectangle((x,672,x+29,698),radius=4,
                            fill=(36,62,76),outline=metal,width=3)
        active=p>.22+(i*.12)
        d.ellipse((x+6,679,x+22,692),
                  fill=accent if active else (72,92,104))


def _generator(d,profile,p):
    metal,accent=profile["metal"],profile["accent"]
    # Exposed drive-shaft and overhead ducts, with a purposeful panel.
    d.polygon(((196,681),(376,682),(365,741),(199,733)),
              fill=(46,68,86),outline=metal,width=5)
    for x in (216,269,322):
        d.ellipse((x,695,x+36,730),fill=(29,48,67),outline=(186,168,134),width=4)
        d.arc((x+7,702,x+29,723),0,225,fill=accent,width=3)
    for i in range(4):
        x=197+i*47
        d.line(((x,755),(x+9,833)),fill=metal,width=8)
    d.rounded_rectangle((189,853,340,980),radius=12,
                        fill=(51,69,88),outline=accent,width=5)
    for i in range(5):
        d.rounded_rectangle((204,871+i*18,316,879+i*18),radius=3,
                            fill=(75,104,121))
    d.ellipse((217,904,264,951),fill=(24,44,62),outline=(220,176,113),width=5)
    d.line(((241,930),(245+round(13*p),919)),fill=(196,222,208),width=4)
    # Copper return pipe on far wall.
    _stroke(d,((837,674),(844,722),(889,748),(891,831)),
            (185,144,98),7)


def _archive(d,profile,p):
    accent,metal,light=profile["accent"],profile["metal"],profile["light"]
    # Pinned evidence board and layered paper silhouettes. Not a generic card:
    # its geometry is consistent across the linked photo-story episodes.
    d.rounded_rectangle((198,681,412,959),radius=8,
                        fill=(56,58,72),outline=(147,127,112),width=7)
    for j,(x,y) in enumerate(((214,702),(298,723),(237,829),(314,848))):
        d.rectangle((x,y,x+65,y+92),
                    fill=(196,186,167),outline=(77,83,97),width=3)
        d.rectangle((x+7,y+8,x+58,y+58),fill=(89+j*12,105,122))
        d.ellipse((x+21,y+19,x+42,y+40),fill=(173,134,119))
        d.polygon(((x+10,y+55),(x+56,y+55),(x+60,y+71),(x+6,y+71)),
                  fill=(72,98,118))
        d.ellipse((x+25,y-7,x+37,y+5),fill=light)
    d.line(((261,748),(326,872),(367,758)),fill=accent,width=4)
    # Hanging file labels vary only by deterministic story progress.
    for i in range(4):
        x=773+i*44
        d.polygon(((x,700),(x+29,700),(x+33,731),(x-2,731)),
                  fill=(143,126,124),outline=metal,width=3)
        d.line(((x+5,715),(x+23,715)),fill=(228,206,173),width=3)
    d.arc((780,766,911,898),195,346,fill=accent,width=4)


def _city(d,profile,p):
    accent,metal,light=profile["accent"],profile["metal"],profile["light"]
    # Distant city silhouettes flank rather than bury the central source art.
    for i,(x,width,height) in enumerate(((196,63,193),(262,50,245),(825,56,222),(885,45,188))):
        y=1060-height
        d.polygon(((x,y+20),(x+width//2,y),(x+width,y+20),(x+width,1110),(x,1110)),
                  fill=(36,57,79),outline=metal,width=4)
        for row in range(3):
            for col in range(2):
                xx=x+12+col*22; yy=y+43+row*36
                if xx+9<x+width:
                    d.rectangle((xx,yy,xx+9,yy+18),fill=(20,34,57))
    # Radio-tower signal over the deserted skyline, dim and deliberate.
    d.line(((912,870),(912,768)),fill=light,width=6)
    for radius in (24,48,73):
        d.arc((912-radius,768-radius,912+radius,768+radius),
              195,345,fill=accent,width=3)
    # Horizon haze is a line, not an opaque replacement of the window.
    for i in range(3):
        y=1082+i*16
        d.line(((181,y),(910,y)),fill=(62+i*8,91+i*8,125+i*6),width=2)


def _timeline(d,profile,p):
    accent,metal,light=profile["accent"],profile["metal"],profile["light"]
    # Independent matching instruments on opposite sides frame both Maras.
    for x in (200,856):
        d.ellipse((x-47,671,x+47,766),fill=(38,54,79),outline=metal,width=6)
        d.ellipse((x-32,687,x+32,750),outline=accent,width=5)
        angle=(.16+2.5*p)*(-1 if x<540 else 1)
        xx=x+round(math.cos(angle)*24)
        yy=720+round(math.sin(angle)*24)
        _stroke(d,((x,720),(xx,yy)),light,5)
        d.rounded_rectangle((x-35,788,x+35,819),radius=6,
                            fill=(62,77,99),outline=accent,width=4)
        for i in range(3):
            d.ellipse((x-22+i*21,799,x-14+i*21,807),
                      fill=(196,168,127))
    # Two opposing tracks converge on a central decision, but the background
    # window remains fully visible between the two instrument columns.
    _stroke(d,((183,1080),(343,1104),(452,1134)),accent,5)
    _stroke(d,((907,1080),(748,1104),(637,1134)),light,5)


def _ocean(d,profile,p):
    accent,metal,light=profile["accent"],profile["metal"],profile["light"]
    # Bathymetric survey console and a reusable glowing navigation instrument.
    d.rounded_rectangle((192,699,374,862),radius=13,
                        fill=(39,65,86),outline=metal,width=6)
    for r in (24,53,77):
        d.arc((283-r,782-r,283+r,782+r),180,358,fill=accent,width=3)
    d.line(((283,782),(283+round(61*math.cos(p*2.8)),
                      782+round(61*math.sin(p*2.8)))),
           fill=light,width=4)
    # Depth contour chart below the panel, in thin lines that let art show.
    for i in range(4):
        x=790+i*27
        d.arc((x-36,795+i*18,x+36,920+i*19),
              195,344,fill=accent,width=4)
    d.rounded_rectangle((795,931,925,982),radius=8,
                        fill=(41,69,91),outline=(134,181,193),width=5)
    for i in range(6):
        d.line(((806+i*18,943),(806+i*18,971)),fill=light if i%2 else accent,width=3)


PROFILE_DRAWERS = {
    "radio_workshop": _workshop,
    "generator_bay": _generator,
    "memory_archive": _archive,
    "silent_city": _city,
    "split_timelines": _timeline,
    "ocean_chart": _ocean,
}


def draw_environment_art(image: Image.Image, action: str, t: float, duration: float):
    """Draw reusable original environment details behind main scene props."""
    _require_frame(image,action,t,duration)
    profile=SET_PROFILES[action]
    from astra_v2.human_action_choreography import action_state
    state=action_state(action,t,duration)
    PROFILE_DRAWERS[profile](ImageDraw.Draw(image), MATERIALS[profile],state.progress)
    return {"profile":profile,"source":"original-cpu-art-library",
            "asset_count":6,"action":action}


def draw_character_materials(draw, x:int, y:int, t:float):
    """Consistent hand-authored outfit detailing on Mara and her double.

    The costume is unchanged by emotion and narration: the same enamel pin,
    teal-seamed jacket, belt/hardware and fabric folds identify the character.
    Called *after* the torso fill and before arms, keeping anatomy readable.
    """
    if not all(isinstance(v,(int,float)) and math.isfinite(v)
               for v in (x,y,t)):
        raise CreativeReject("Invalid character material coordinates")
    # Highlight/cel shading, scientific insignia and embroidered garment.
    _stroke(draw,((x-46,y-56),(x-33,y+20),(x-57,y+139)),
            (33,91,108),8)
    _stroke(draw,((x+48,y-57),(x+53,y+28),(x+70,y+172)),
            (93,169,174),6)
    _stroke(draw,((x-35,y+160),(x+41,y+164)),(37,73,92),6)
    _stroke(draw,((x-29,y+180),(x+35,y+183)),(191,152,102),10)
    draw.rounded_rectangle((x-7,y+174,x+11,y+192),radius=4,
                           fill=(202,179,139),outline=(39,58,76),width=3)
    # Tiny observatory pin stays character-specific; it is not an external logo.
    draw.ellipse((x+24,y-28,x+44,y-8),
                 fill=(215,173,109),outline=(26,61,83),width=2)
    _stroke(draw,((x+30,y-18),(x+38,y-18)),(52,107,132),3)
    # Three fabric seam folds with subdued light modulation.
    shine=4+int(abs(math.sin(t*.46))*3)
    for i in range(3):
        xx=x-24+i*24
        _stroke(draw,((xx,y+90),(xx+shine,y+130)),
                (79+i*7,141+i*6,149+i*4),3)
    # Individual boot heels, always under their corresponding silhouette.
    for side in (-1,1):
        cx=x+side*68
        draw.rounded_rectangle((cx-25,y+331,cx+27,y+347),
                               radius=5,fill=(23,35,52),outline=(93,101,119),width=3)
    return "mara-scientist-costume-v1"
