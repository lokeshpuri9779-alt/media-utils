"""Story-specific CPU-animated human performances for The Tomorrow Signal.

This is a bounded, original 2D character performance, not generic clipart,
real-person imagery, neural video, or proof of general-purpose human animation.
Unknown actors/actions are rejected rather than falling back to a signal icon.
"""
from __future__ import annotations

import math

from PIL import ImageDraw

from astra_errors import CreativeReject

PILOT_ID = "rayvan-season-01-episode-01"
EPISODE_TWO_ID = "rayvan-season-01-episode-02"
EPISODE_THREE_ID = "rayvan-season-01-episode-03"
EPISODE_FOUR_ID = "rayvan-season-01-episode-04"
ACTIONS = (
    "discover_radio",
    "trace_cable",
    "hear_warning",
    "flee_door",
)
EPISODE_TWO_ACTIONS = (
    "guard_knocking_door",
    "inspect_generator_clue",
    "inspect_future_photograph",
    "stop_stranger_switch",
)
EPISODE_THREE_ACTIONS = (
    "survey_dead_city",
    "inspect_reverse_clock",
    "study_altered_photographs",
    "confront_mara_double",
)
EPISODE_FOUR_ACTIONS = (
    "face_duplicate_at_countdown",
    "warn_parallel_cities",
    "split_glass_key",
    "seal_and_reveal_sea_door",
)
EPISODE_ACTIONS = {
    PILOT_ID: ACTIONS,
    EPISODE_TWO_ID: EPISODE_TWO_ACTIONS,
    EPISODE_THREE_ID: EPISODE_THREE_ACTIONS,
    EPISODE_FOUR_ID: EPISODE_FOUR_ACTIONS,
}
INK = (24, 34, 49)
SKIN = (198, 142, 111)
HAIR = (42, 37, 51)
JACKET = (51, 121, 139)
PANTS = (42, 55, 79)
RADIO = (62, 73, 93)
GOLD = (249, 190, 92)

# Every approved beat gets an authored performance intent, instead of the
# same facial expression and raised arm throughout the full story. The double
# can override the protagonist's mood in explicitly choreographed scenes.
PERFORMANCE = {
    "discover_radio": ("curious", 1, "consider"),
    "trace_cable": ("focused", -1, "consider"),
    "hear_warning": ("afraid", 1, "protect"),
    "flee_door": ("afraid", -1, "protect"),
    "guard_knocking_door": ("suspicious", 1, "protect"),
    "inspect_generator_clue": ("focused", 1, "consider"),
    "inspect_future_photograph": ("startled", 1, "protect"),
    "stop_stranger_switch": ("defiant", 1, "open"),
    "survey_dead_city": ("afraid", 1, "protect"),
    "inspect_reverse_clock": ("puzzled", 1, "consider"),
    "study_altered_photographs": ("grieving", 1, "consider"),
    "confront_mara_double": ("startled", 1, "open"),
    "face_duplicate_at_countdown": ("suspicious", 1, "open"),
    "warn_parallel_cities": ("urgent", 1, "open"),
    "split_glass_key": ("determined", 1, "open"),
    "seal_and_reveal_sea_door": ("hopeful", 1, "consider"),
}


def validate_human_scene(shot):
    """Permit only explicitly storyboarded actions in two known serialized episodes."""
    story_id = shot.get("story_visual_seed")
    allowed = EPISODE_ACTIONS.get(story_id)
    if allowed is None:
        raise CreativeReject("Human performer not approved for this story identity")
    if shot.get("story_human_actor") != "mara":
        raise CreativeReject("Unknown human actor; no procedural fallback")
    action = shot.get("story_human_action")
    if action not in allowed:
        raise CreativeReject("Unrenderable human action for this episode: " + str(action))
    if shot.get("story_cast"):
        raise CreativeReject("Human episode does not support an animal cast")
    narration = str(shot.get("speech") or "").lower()
    if not narration.strip():
        raise CreativeReject("Missing narrated human action")
    if story_id == PILOT_ID:
        if action in ("discover_radio", "trace_cable") and "radio" not in narration:
            raise CreativeReject("Radio action lacks a narrated radio")
        if action == "hear_warning" and not any(word in narration for word in ("voice", "countdown", "blackout")):
            raise CreativeReject("Warning scene lacks a narrated warning")
        if action == "flee_door" and not any(word in narration for word in ("door", "stairs")):
            raise CreativeReject("Escape scene has no door or stairs")
        expected = "signal" if action in ("discover_radio", "trace_cable") else "door"
    elif story_id == EPISODE_TWO_ID:
        required_terms = {
            "guard_knocking_door": ("knocked", "door"),
            "inspect_generator_clue": ("generator", "notebook"),
            "inspect_future_photograph": ("photograph", "stranger", "key"),
            "stop_stranger_switch": ("stranger", "switch", "lights"),
        }
        if not all(term in narration for term in required_terms[action]):
            raise CreativeReject("Episode 2 actor action does not match narrated event")
        expected = "door"
    elif story_id == EPISODE_THREE_ID:
        required_terms = {
            "survey_dead_city": ("city", "door", "footprints"),
            "inspect_reverse_clock": ("clock", "threshold", "radio"),
            "study_altered_photographs": ("jacket", "photographs", "stranger"),
            "confront_mara_double": ("another mara", "key", "radios"),
        }
        if not all(term in narration for term in required_terms[action]):
            raise CreativeReject("Episode 3 actor action does not match narrated event")
        expected = "door"
    else:
        required_terms = {
            "face_duplicate_at_countdown": ("two versions", "key", "radios"),
            "warn_parallel_cities": ("other mara", "erased", "passage"),
            "split_glass_key": ("broke", "key", "countdown"),
            "seal_and_reveal_sea_door": ("door sealed", "stars", "notebook"),
        }
        if not all(term in narration for term in required_terms[action]):
            raise CreativeReject("Episode 4 actor action does not match narrated event")
        expected = "door"
    if str(shot.get("visual") or "").lower() != expected:
        raise CreativeReject("Human action requires authored " + expected + " visual")
    return "human"

def _line(draw, coordinates, color=INK, width=12):
    draw.line(coordinates, fill=color, width=width, joint="curve")


def _radio(draw, x, y, t, *, glow=True, portable=False):
    """Handmade radio with moving frequency pulse and distinct readable antenna."""
    w, h = (180, 135) if portable else (225, 180)
    draw.rounded_rectangle((x-w//2, y-h//2, x+w//2, y+h//2),
                           radius=19, fill=RADIO, outline=(167, 180, 195), width=7)
    draw.rounded_rectangle((x-w//2+20, y-h//2+25, x+w//2-20, y+17),
                           radius=10, fill=(13, 26, 45), outline=(91, 145, 171), width=4)
    for k in range(8):
        xx=x-w//2+28+k*(w-55)//7
        height=int(8+23*(.5+.5*math.sin(t*7+k*.95)))
        _line(draw, ((xx,y+6-height//2),(xx,y+6+height//2)),
              (120, 219, 226) if glow else (93, 132, 155), 4)
    draw.ellipse((x+w//2-48, y+h//2-44, x+w//2-22, y+h//2-18),
                 fill=GOLD if glow and int(t*4)%2==0 else (110, 107, 97))
    _line(draw, ((x-w//2+45,y-h//2),(x-w//2+2,y-h//2-62)), (178, 197, 205), 7)
    return (x-w//2, y-h//2, x+w//2, y+h//2)


def _door(draw, open_amount):
    """A physical door changing its opening, not a decorative portal glyph."""
    draw.polygon(((660,606),(947,606),(1007,1200),(619,1200)),
                 fill=(23, 32, 49), outline=(197, 156, 118), width=15)
    draw.polygon(((697,640),(920,638),(950,1155),(655,1155)),
                 fill=(13, 17, 35))
    travel=int(160*open_amount)
    draw.polygon(((682,655),(902-travel,680),(916-travel,1127),(672,1150)),
                 fill=(95, 72, 98), outline=(211, 187, 166), width=9)
    draw.ellipse((853-travel,895,872-travel,916), fill=GOLD)
    # Escape glow stays within the stage, separate from title/captions.
    for k in range(3):
        xx=920+k*20
        _line(draw, ((xx,695),(xx,1115)), (70+k*25, 112+k*19, 157+k*14), 5)


def _draw_mara_face(draw, x, y, t, *, emotion="curious", gaze=0,
                    expression_strength=1.0, head_yaw=0.0):
    """Readable brows, eyes and mouth without changing Mara's head design.

    Emotions are author-selected for each narrated action; animation is
    deterministic and deliberately NOT a false claim of phoneme lip-sync.
    """
    moods = {
        "curious": (5, -1, "smile"),
        "focused": (0, -6, "line"),
        "afraid": (12, -10, "open"),
        "suspicious": (3, 6, "flat"),
        "startled": (15, -8, "open"),
        "defiant": (-5, 9, "flat"),
        "puzzled": (4, 4, "wry"),
        "grieving": (-4, -1, "frown"),
        "urgent": (9, 1, "open"),
        "determined": (-7, 8, "line"),
        "hopeful": (6, -5, "smile"),
        "knowing": (0, 4, "smirk"),
    }
    if emotion not in moods or gaze not in (-1, 0, 1):
        raise CreativeReject("Unsupported authored Mara emotion or gaze")
    if not isinstance(expression_strength,(int,float)) or not math.isfinite(expression_strength) or not 0<=expression_strength<=1:
        raise CreativeReject("Unsupported facial expression intensity")
    if not isinstance(head_yaw,(int,float)) or not math.isfinite(head_yaw) or abs(head_yaw)>.75:
        raise CreativeReject("Unreviewed human face orientation")
    raise_brow, slope, mouth = moods[emotion]
    # A quarter-turn compresses the visible eye spacing and moves the facial
    # center toward the silhouette's near cheek, without changing identity.
    face_x = x+round(18*head_yaw)
    compression = 1-.53*abs(head_yaw)
    raise_brow=round(raise_brow*expression_strength)
    slope=round(slope*expression_strength)
    eye_y = y - 170
    blink = (t % 3.4) < .105
    eye_shift = int(gaze * 5 + 2 * math.sin(t * .68))
    for dx in (-28, 30):
        ex=face_x+round(dx*compression)
        if blink:
            _line(draw, ((ex-12, eye_y), (ex+11, eye_y)), INK, 4)
        else:
            eye_radius=round(12-5*abs(head_yaw)*(1 if dx*head_yaw<0 else .25))
            draw.ellipse((ex-eye_radius, eye_y-12, ex+eye_radius, eye_y+11),
                         fill=(245, 244, 239), outline=HAIR, width=2)
            px=ex+round(eye_shift*compression)
            draw.ellipse((px-6, eye_y-8, px+6, eye_y+8), fill=INK)
            draw.ellipse((px-3, eye_y-6, px, eye_y-3), fill=(235, 235, 226))
        # Brow angles read at normal 1080x1920 viewing resolution.
        offset=raise_brow+(3 if dx<0 and emotion=="suspicious" else 0)
        draw.line(((ex-15, eye_y-24-offset-slope),
                   (ex+15, eye_y-24-offset+slope)), fill=HAIR, width=7)
    # The off-center nose/cheek gives a legible three-quarter view at mobile
    # resolution. In the front view these extra strokes are absent.
    if abs(head_yaw)>.18:
        nx=face_x+round(14*head_yaw)
        draw.line(((nx,y-158),(nx+round(12*head_yaw),y-139),
                   (nx-3,y-136)),fill=(161,91,91),width=4,joint="curve")
        cheek_x=face_x-round(31*head_yaw)
        draw.arc((cheek_x-9,y-138,cheek_x+13,y-121),10,95,
                 fill=(209,132,112),width=3)
    mx=face_x+round(5*head_yaw)
    if mouth=="open":
        opening=round(3+6*expression_strength+2*math.sin(t*2.4)*expression_strength)
        draw.ellipse((mx-12, y-123-opening, mx+12, y-109+opening),
                     fill=(75, 40, 54), outline=(145, 80, 87), width=2)
    elif mouth=="frown":
        draw.arc((mx-24,y-116,mx+25,y-85),178,354,fill=(111,62,70),width=6)
    elif mouth in ("flat", "line"):
        _line(draw, ((mx-18,y-109),(mx+18,y-109+(3 if mouth=="flat" else 0))),
              (111,62,70), 5)
    elif mouth in ("wry","smirk"):
        _line(draw, ((mx-18,y-117),(mx+18,y-109 if mouth=="smirk" else y-115)),
              (111,62,70), 5)
    else:
        draw.arc((mx-25,y-139,mx+28,y-106),0,178,fill=(111,62,70),width=6)


def _mara(draw, x, y, t, *, reaching=False, alarm=False, running=False,
          carrying=False, emotion="curious", gaze=0, gesture="consider",
          lean=0.0, expression_strength=1.0, head_yaw=0.0):
    """Persistent character with two-joint limbs and authored facial acting."""
    if not math.isfinite(t):
        raise CreativeReject("Actor animation time must be finite")
    if not isinstance(lean,(int,float)) or not math.isfinite(lean) or abs(lean)>24:
        raise CreativeReject("Unsupported torso lean")
    if not isinstance(head_yaw,(int,float)) or not math.isfinite(head_yaw) or abs(head_yaw)>.75:
        raise CreativeReject("Unsupported head direction")
    if gesture not in ("consider", "protect", "open"):
        raise CreativeReject("Unsupported actor hand gesture")
    from astra_v2.human_skeletal_rig import solve_mara_pose, HIP_L, HIP_R
    pose=solve_mara_pose(t,reaching=reaching,running=running,
                         carrying=carrying,gesture=gesture)
    bounce=int(6*math.sin(t*2.8))
    if running:
        bounce=int(15*math.sin(t*11))
    x+=round(pose.torso_offset*.45)
    y+=bounce
    # Forward-kinematic painted thigh/shin segments follow the real two-bone
    # knee solution. Opposed ankle strides distinguish walking/running from
    # a stationary upper-body wiggle.
    for hip,knee,ankle in (
        (HIP_L,pose.left_knee,pose.left_ankle),
        (HIP_R,pose.right_knee,pose.right_ankle),
    ):
        _line(draw,((x+round(hip[0]),y+round(hip[1])),
                    (x+round(knee[0]),y+round(knee[1])),
                    (x+round(ankle[0]),y+round(ankle[1]))),PANTS,36)
        draw.ellipse((x+round(knee[0])-18,y+round(knee[1])-18,
                      x+round(knee[0])+18,y+round(knee[1])+18),
                     fill=(54,67,90),outline=INK,width=4)
    for ankle,side in ((pose.left_ankle,-1),(pose.right_ankle,1)):
        foot_x=x+round(ankle[0])
        foot_y=y+round(ankle[1])
        draw.rounded_rectangle((foot_x-38 if side<0 else foot_x-20,
                                foot_y-12,
                                foot_x+22 if side<0 else foot_x+40,
                                foot_y+16),radius=10,fill=INK,
                               outline=(85,102,116),width=3)
    # Shoulder-led head turn and body lean: lower leg anchor remains planted.
    head_x=x+round(1.15*lean)
    shoulder_x=x+round(lean)
    # Fixed outfit and hairstyle preserve serialized Mara continuity.
    draw.ellipse((head_x-113,y-220,head_x-39,y-85),fill=HAIR)
    draw.ellipse((head_x-87,y-282,head_x+91,y-71),fill=HAIR,outline=INK,width=8)
    # Turn toward the prop: visible skin narrows and shifts under unchanged
    # hair volume, allowing quarter-profile looks without a 3D head mesh.
    face_narrow=round(11*abs(head_yaw))
    face_shift=round(7*head_yaw)
    draw.ellipse((head_x-66+face_narrow+face_shift,y-253,
                  head_x+70-face_narrow+face_shift,y-94),
                 fill=SKIN,outline=INK,width=6)
    if abs(head_yaw)>.18:
        ear_x=head_x+round(62*(1 if head_yaw>0 else -1))
        draw.ellipse((ear_x-10,y-177,ear_x+10,y-146),
                     fill=SKIN,outline=(145,83,89),width=3)
    draw.polygon(((head_x-75,y-251),(head_x-11,y-279),(head_x+89,y-218),(head_x+57,y-248),
                  (head_x+19,y-228),(head_x-72,y-208)), fill=HAIR)
    draw.arc((head_x-74,y-271,head_x+79,y-130),204,295,fill=(91,75,96),width=5)
    draw.arc((head_x-56,y-246,head_x+57,y-112),180,242,fill=(232,174,140),width=4)
    _draw_mara_face(draw,head_x,y,t,emotion=emotion,gaze=gaze,
                    expression_strength=expression_strength,head_yaw=head_yaw)
    draw.polygon(((shoulder_x-51,y-80),(shoulder_x+49,y-80),
                  (x+86,y+210),(x-91,y+210)),
                 fill=JACKET,outline=INK,width=8)
    # Layered costume shading: avoid one uniform flat teal slab. Panels follow
    # the same character identity in all four episodes and both timelines.
    draw.polygon(((x-47,y-64),(x-18,y-80),(x-34,y+155),(x-78,y+181)),
                 fill=(36,91,113))
    draw.polygon(((x+48,y-68),(x+68,y+147),(x+36,y+176),(x+23,y-61)),
                 fill=(75,151,161))
    draw.polygon(((x-23,y-76),(x+23,y-76),(x+11,y+180),(x-14,y+180)),
                 fill=(215, 224, 216))
    draw.line(((x-42,y-67),(x-20,y+107)),fill=(111,181,186),width=5)
    draw.line(((x+45,y-62),(x+28,y+121)),fill=(119,191,191),width=4)
    draw.polygon(((x+27,y-38),(x+47,y-18),(x+13,y+13)),
                 fill=(198,212,205))
    draw.line(((x,y-64),(x,y+188)),fill=(20,65,85),width=6)
    draw.ellipse((x-8,y+125,x+8,y+141),fill=GOLD)
    # Reusable authored clothing details are shared by Mara and her double,
    # rather than regenerating a different costume for every scene.
    from astra_v2.human_illustrated_materials import draw_character_materials
    draw_character_materials(draw,x,y,t)
    # Articulated shoulder -> elbow -> wrist bones solve every frame.
    # Previously elbow points were just arbitrary fractions along one
    # immovable-looking sleeve, with no true joint-length constraints.
    for shoulder,elbow,hand in (
        ((-58,-40),pose.left_elbow,pose.left_hand),
        ((54,-40),pose.right_elbow,pose.right_hand),
    ):
        points=[(shoulder_x+round(px),y+round(py)) for px,py in (shoulder,elbow,hand)]
        _line(draw,points,JACKET,32)
        ex,ey=points[1]
        draw.ellipse((ex-17,ey-17,ex+17,ey+17),
                     fill=(67,137,150),outline=INK,width=3)
        hx,hy=points[2]
        draw.ellipse((hx-17,hy-17,hx+17,hy+17),
                     fill=SKIN,outline=INK,width=3)
    # The exact wrist pixels used above are exported to author attached props.
    # This prevents another renderer inventing independent sinusoidal paths.
    return {
        "left_hand": (shoulder_x+round(pose.left_hand[0]),y+round(pose.left_hand[1])),
        "right_hand": (shoulder_x+round(pose.right_hand[0]),y+round(pose.right_hand[1])),
    }


def _generator(draw, t):
    """Stationary emergency generator; toggling switch is a separate later event."""
    draw.rounded_rectangle((650,945,973,1159),radius=25,
                           fill=(81,91,103),outline=(204,181,130),width=9)
    draw.rectangle((710,986,891,1046),fill=(20,37,54),outline=(119,167,179),width=5)
    for k in range(5):
        x=729+k*30
        draw.line(((x,999),(x,1035)),fill=(77,204,191),width=5)
    draw.ellipse((711,1103,752,1141),fill=(193,164,114))
    draw.ellipse((858,1103,899,1141),fill=(193,164,114))
    draw.line(((918,971),(935,925)),fill=(205,201,191),width=12)
    draw.ellipse((924,914,946,936),fill=(238,190,92))


def _notebook(draw, t):
    """Close foreground notebook, carrying the repeated mark."""
    x=280+int(4*math.sin(t*2.3))
    y=1080
    draw.polygon(((x,y),(x+230,y-14),(x+248,y+106),(x+10,y+128)),
                 fill=(188,161,118),outline=INK,width=7)
    draw.polygon(((x+20,y+15),(x+218,y+2),(x+230,y+85),(x+30,y+105)),
                 fill=(230,222,194))
    # Shared glyph from the generator switch, a diamond with a divider.
    draw.polygon(((x+125,y+32),(x+151,y+59),(x+125,y+86),(x+99,y+59)),
                 outline=(65,109,131),width=6)
    _line(draw,((x+102,y+60),(x+148,y+60)),(65,109,131),4)


def _stranger(draw, x, y, t, *, touching_switch=False):
    """Distinct stranger silhouette; do not invent the missing brother's appearance."""
    bob=int(5*math.sin(t*1.9))
    y+=bob
    draw.ellipse((x-77,y-208,x+77,y-66),fill=(85,86,114),outline=INK,width=7)
    draw.ellipse((x-62,y-179,x+62,y-83),fill=(68,63,89))
    draw.polygon(((x-77,y-79),(x+75,y-79),(x+107,y+226),(x-110,y+226)),
                 fill=(93,75,114),outline=INK,width=8)
    draw.polygon(((x-81,y-95),(x+81,y-95),(x+59,y-235),(x-62,y-235)),
                 fill=(48,44,69),outline=INK,width=5)
    _line(draw,((x-74,y-40),(x-131,y+155)),(93,75,114),35)
    hand=(x+156,y-3) if touching_switch else (x+125,y+112)
    _line(draw,((x+73,y-38),hand),(93,75,114),34)
    draw.ellipse((hand[0]-15,hand[1]-15,hand[0]+15,hand[1]+15),
                 fill=(159,121,118),outline=INK,width=3)
    _line(draw,((x-43,y+215),(x-59,y+346)),PANTS,35)
    _line(draw,((x+42,y+215),(x+64,y+346)),PANTS,35)


def _future_photograph(draw):
    """The future, Mara and her brother are depicted only *inside* a dated photo."""
    draw.rounded_rectangle((530,780,944,1130),radius=14,
                           fill=(219,212,191),outline=INK,width=10)
    draw.rectangle((563,816,914,1067),fill=(86,113,131))
    # Silhouettes within the picture, not extra live actors.
    for x,shade in ((650,(63,57,69)),(807,(86,73,94))):
        draw.ellipse((x-33,855,x+33,921),fill=shade)
        draw.polygon(((x-53,916),(x+53,916),(x+69,1025),(x-67,1025)),fill=shade)
    draw.polygon(((749,937),(765,920),(781,937),(765,957)),
                 fill=(72,171,230),outline=(208,239,255),width=4)
    draw.rectangle((626,1080,852,1094),fill=(119,102,97))


def _city_power(draw, t):
    """Exterior lighting progressively returns while the stranger flips a switch."""
    for j in range(6):
        x=108+j*133
        height=110+(j%3)*42
        draw.rectangle((x,1015-height,x+84,1015),fill=(44,58,78))
        for k in range(2):
            for m in range(3):
                lit=t>=.55+j*.32
                col=(245,196,107) if lit else (40,47,63)
                draw.rectangle((x+15+k*34,1015-height+15+m*29,
                                x+27+k*34,1015-height+27+m*29),fill=col)


def _alternate_city(draw, t, *, progress=1.0):
    """Vacant, starless skyline through the open observatory doorway."""
    draw.polygon(((680,695),(955,695),(981,1164),(667,1164)),
                 fill=(9,17,33),outline=(142,170,186),width=5)
    # Perspective city remains abandoned: dark windows, no living silhouettes.
    for index in range(5):
        x=683+index*52
        y=839-(index%3)*42
        draw.rectangle((x,y,x+44,1137),fill=(38,59,77))
        for j in range(3):
            draw.rectangle((x+8,y+23+j*40,x+19,y+38+j*40),fill=(13,24,41))
    # Floor footprints advance toward the camera in alternating steps.
    for i in range(min(4,max(0,round(progress*4)))):
        x=715+(i%2)*58+int(6*math.sin(t*.8))
        y=1028+i*44
        draw.ellipse((x,y,x+28,y+16),fill=(144,150,154))


def _reverse_clock(draw,t):
    """Clock's single moving hand unmistakably runs counter-clockwise."""
    x,y,r=748,876,154
    draw.ellipse((x-r,y-r,x+r,y+r),fill=(216,208,176),outline=INK,width=11)
    for hour in range(12):
        a=hour*math.tau/12-math.pi/2
        _line(draw,((int(x+126*math.cos(a)),int(y+126*math.sin(a))),
                    (int(x+141*math.cos(a)),int(y+141*math.sin(a)))),INK,6)
    angle=-math.pi/2-t*.95
    _line(draw,((x,y),(int(x+104*math.cos(angle)),int(y+104*math.sin(angle)))),INK,12)
    _line(draw,((x,y),(int(x+65*math.cos(angle*.35)),int(y+65*math.sin(angle*.35)))),(89,110,119),8)
    draw.ellipse((x-11,y-11,x+11,y+11),fill=INK)
    # Physical radio provides the second narrated story object.
    _radio(draw,736,1113,t,portable=True)


def _photo_wall(draw,t):
    """Readable photographic montage; the same Mara appears in divergent outcomes."""
    for col in range(3):
        x=615+col*109
        y=686+(col%2)*42
        draw.rounded_rectangle((x,y,x+92,y+165),radius=5,
                               fill=(222,212,188),outline=INK,width=5)
        draw.rectangle((x+12,y+12,x+80,y+133),fill=(91+col*7,106,123))
        draw.ellipse((x+28,y+39,x+65,y+83),fill=SKIN)
        draw.polygon(((x+22,y+82),(x+70,y+82),(x+79,y+124),(x+13,y+124)),
                     fill=JACKET if col!=1 else (132,90,104))
    # Brother's abandoned jacket and changed label beside the photographs.
    draw.polygon(((707,1020),(746,992),(769,1013),(795,994),(841,1032),
                  (882,1124),(835,1141),(819,1093),(811,1191),
                  (712,1191),(704,1093),(680,1139),(645,1115)),
                 fill=(114,100,86),outline=INK,width=7)
    draw.rectangle((754,1045,806,1068),fill=(222,210,176),outline=INK,width=3)
    # Pinwheel marks imply alternate choices without false full-motion claims.
    q=4*math.sin(t*2)
    draw.line(((570,830+q),(593,849+q)),fill=GOLD,width=7)


def _blue_glass_key(draw,x,y):
    """Recurring unique blue-glass prop, recognizable across this episode."""
    color=(72,171,233)
    draw.ellipse((x-28,y-26,x+27,y+26),fill=(42,108,178),outline=(198,236,255),width=7)
    draw.ellipse((x-11,y-10,x+10,y+11),fill=(17,48,94))
    _line(draw,((x+7,y+16),(x+8,y+108)),color,16)
    _line(draw,((x+8,y+78),(x+40,y+78)),color,12)
    _line(draw,((x+8,y+103),(x+31,y+103)),color,10)


def _dual_city_futures(draw,t):
    """Two incompatible futures, one lit and one starless, without invented people."""
    draw.rectangle((665,682,812,1080),fill=(39,55,74),outline=(154,165,181),width=4)
    draw.rectangle((824,682,969,1080),fill=(14,20,40),outline=(111,119,144),width=4)
    for side,lit in ((680,True),(840,False)):
        for k in range(3):
            x=side+k*38
            height=128+(k%2)*76
            draw.rectangle((x,1046-height,x+31,1046),fill=(61,82,99))
            for j in range(3):
                draw.rectangle((x+10,1046-height+15+j*30,x+19,1046-height+25+j*30),
                               fill=(245,194,112) if lit and t<2.7 else (21,30,48))
    _line(draw,((813,693),(813,1080)),(178,159,194),7)


def _key_halves(draw,t):
    """Two physical broken key pieces separate and transfer to the double."""
    separation=int(8+min(1,max(0,t-.38)/1.3)*103)
    cx,cy=540,932
    color=(65,162,232)
    draw.ellipse((cx-52-separation,cy-27,cx-4-separation,cy+27),
                 fill=color,outline=(191,238,255),width=6)
    draw.ellipse((cx-36-separation,cy-9,cx-22-separation,cy+10),fill=(20,63,116))
    _line(draw,((cx-8-separation,cy+14),(cx-8-separation,cy+105)),color,14)
    draw.polygon(((cx+4+separation,cy-25),(cx+52+separation,cy-25),
                  (cx+31+separation,cy+28),(cx+10+separation,cy+28)),
                 fill=color,outline=(191,238,255),width=6)
    _line(draw,((cx+30+separation,cy+21),(cx+30+separation,cy+104)),color,14)
    _line(draw,((cx+30+separation,cy+73),(cx+59+separation,cy+73)),color,12)
    if .42<t<1.15:
        for k in range(5):
            alpha=1+((k*17+int(t*57))%28)
            draw.ellipse((cx-10+k*9,cy-35-alpha,cx-5+k*9,cy-30-alpha),
                         fill=(141,221,250))


def _sealed_door_stars(draw,t):
    """The door visibly closes; new stars appear only after the seal is made."""
    seal=min(1,max(0,t)/2.3)
    _door(draw,.72*(1-seal))
    if seal>.5:
        for i in range(13):
            x=654+(i*37)%310
            y=637+(i*79)%375
            r=2+(i%3)
            draw.ellipse((x-r,y-r,x+r,y+r),fill=(235,223,184))


def _notebook_sea_ending(draw,t):
    """Page depicts a submerged SECOND door rather than fabricating a new scene."""
    draw.polygon(((607,1000),(952,979),(963,1235),(610,1258)),
                 fill=(224,208,173),outline=INK,width=10)
    draw.polygon(((655,1033),(923,1026),(919,1220),(658,1230)),
                 fill=(105,173,195),outline=(64,111,132),width=4)
    for k in range(4):
        yy=1087+k*34
        draw.arc((669,yy,902,yy+55),0,170,fill=(188,224,225),width=6)
    draw.rectangle((749,1084,845,1214),fill=(42,78,100),outline=(228,236,213),width=8)
    draw.ellipse((819,1140,834,1156),fill=GOLD)
    draw.polygon(((750,1041),(769,1067),(786,1042)),fill=(242,218,157))
    # Page turns very slightly so the reveal is a motion event, not a static card.
    offset=int(5*math.sin(t*1.1))
    draw.line(((626,1006+offset),(620,1232)),fill=(161,138,115),width=8)


def draw_human_scene(image, shot, t):
    """Draw only authenticated pilot action geometry in the 1080x1920 scene stage."""
    validate_human_scene(shot)
    if image.mode != "RGB" or image.size != (1080, 1920):
        raise CreativeReject("Human episode requires RGB 1080x1920 Studio frame")
    action=shot["story_human_action"]
    from astra_v2.human_action_choreography import action_state
    state = action_state(action, t, float(shot.get("duration") or 12))
    mood, look, gesture = PERFORMANCE[action]
    from astra_v2.human_performance_cues import acting_cue
    from astra_v2.human_stage_depth import draw_actor_shadow, draw_observatory_stage
    def performer(draw, x, y, time, **overrides):
        opts = {"emotion": mood, "gaze": look, "gesture": gesture}
        opts.update(overrides)
        # The double gets a separate mirrored posture, not the protagonist's
        # same facing/lean. Both figures use the same original IK skeleton.
        is_double = opts.get("emotion") == "knowing"
        cue = acting_cue(action,t,float(shot.get("duration") or 12),double=is_double)
        opts["lean"]=cue.lean
        opts["expression_strength"]=cue.expression_strength
        # Story-directed quarter-profile viewing is driven by narration time,
        # not the short local reach-motion clock.
        from astra_v2.human_story_composition import view_yaw
        opts["head_yaw"]=view_yaw(action,t,float(shot.get("duration") or 12),
                                  double=is_double)
        walking_offset=round(35*state.movement)
        if opts.get("reaching"):
            opts["reaching"] = state.attention > .14 and state.aftermath < .95
            time = 1.15*state.attention
        # The shadow anchors to the legs rather than following upper-body lean.
        draw_actor_shadow(draw,x+walking_offset,y,
                          running=bool(opts.get("running")),
                          progress=state.progress)
        return _mara(draw, x+walking_offset, y, time, **opts)
    # Keep verified environment imagery visible through the open window.
    draw_observatory_stage(image,action,t,float(shot.get("duration") or 12))
    # Chapter-specific reusable art lives BEHIND the hand-acted character and
    # story object layers. The original verified backdrop remains exposed.
    from astra_v2.human_illustrated_materials import draw_environment_art
    draw_environment_art(image,action,t,float(shot.get("duration") or 12))
    d=ImageDraw.Draw(image)
    if action == "discover_radio":
        _radio(d,750,995,t,glow=state.event > .15)
        _line(d,((750,1080),(750,1195)),(134,112,84),16)
        performer(d,365+int(18*math.sin(t*.5)),885,t,reaching=True)
    elif action == "trace_cable":
        _radio(d,757,945,t)
        # Distinct floor cable connecting radios, read as a traceable object.
        # Light travels along the cable; the discovery is not present at frame one.
        path=((751,1039),(718,1158),(540,1185),(373,1108))
        shown=max(1,round(1+2*state.event))
        _line(d,path[:shown+1],GOLD,10)
        _radio(d,342,1109,t,glow=False,portable=True)
        performer(d,605,873,t,reaching=True)
    elif action == "hear_warning":
        _door(d,0.32+0.08*math.sin(t))
        _radio(d,748,1065,t,glow=True,portable=True)
        # City blackout as an on-screen event, not a static caption.
        for j in range(5):
            cx=688+j*57
            d.rectangle((cx,710,cx+31,812), fill=(27,36,57))
            if state.event < (j+1)/5:
                d.rectangle((cx+7,736,cx+21,755),fill=GOLD)
        performer(d,350,872,t,reaching=True,alarm=True)
    elif action == "flee_door":
        openness=max(.08,.76-state.progress*.63)
        _door(d,openness)
        actor=performer(d,420-round(140*state.attention),881,t,
                        running=True,carrying=True,alarm=True)
        # Receiver and gripping fingers follow the *same* IK wrist coordinates,
        # even when Mara moves left, changes stride or the camera reframes.
        from astra_v2.human_prop_interaction import draw_radio_in_hand
        draw_radio_in_hand(d,actor["right_hand"],t,_radio)
    elif action == "guard_knocking_door":
        _door(d,.22+.045*math.sin(t*3.2))
        # An actual physical knock: repeated displacement at the door panel.
        for phase in range(3 if state.event > .08 else 0):
            x=886+phase*12
            radius=9+phase*10+int(abs(math.sin(t*3.2))*8)
            d.arc((x-radius,872-radius,x+radius,872+radius),
                  -85,85,fill=(130,187,222),width=4)
        _radio(d,350,1111,t,portable=True)
        performer(d,368,857,t,alarm=True)
    elif action == "inspect_generator_clue":
        _generator(d,t)
        if state.attention > .18:
            _notebook(d,t)
        performer(d,375,865,t,reaching=True)
    elif action == "inspect_future_photograph":
        if state.event > .12:
            _future_photograph(d)
        _stranger(d,795,770,t)
        performer(d,327,875,t,reaching=True,alarm=True)
    elif action == "stop_stranger_switch":
        _city_power(d,state.event*3.4)
        _door(d,min(.9,.25+state.event*.65))
        # The stranger actuates a dedicated wall switch; Mara reacts, not assists.
        d.rounded_rectangle((797,724,888,830),radius=12,
                            fill=(117,130,143),outline=INK,width=6)
        d.line(((838,771),(838,738 if state.event > .18 else 804)),
               fill=(248,191,103),width=11)
        _stranger(d,675,856,t,touching_switch=True)
        performer(d,279,870,t,reaching=True,alarm=True)
    elif action == "survey_dead_city":
        _door(d,.82)
        _alternate_city(d,t,progress=state.attention)
        performer(d,337,864,t,reaching=True,alarm=True)
    elif action == "inspect_reverse_clock":
        _door(d,.42)
        _reverse_clock(d,t)
        performer(d,346,865,t,reaching=True,alarm=True)
    elif action == "study_altered_photographs":
        if state.attention > .15:
            _photo_wall(d,t)
        performer(d,343,868,t,reaching=True,alarm=True)
    elif action == "confront_mara_double":
        _door(d,.73)
        # An independently moving matching human puppet, not a stranger/animal.
        # The double wears Mara's same palette and silhouette for continuity.
        performer(d,307,865,t,reaching=True,alarm=True)
        if state.attention > .40:
            performer(d,748+int(10*math.sin(t*.85)),865,t,reaching=True,alarm=True,
                  emotion="knowing",gaze=-1)
        if state.event > .10:
            _blue_glass_key(d,866,969+int(6*math.sin(t*1.6)))
        _radio(d,255,1131,t,portable=True)
        _radio(d,865,1131,t,portable=True)
    elif action == "face_duplicate_at_countdown":
        _door(d,.68)
        performer(d,312,861,t,reaching=True,alarm=True)
        performer(d,775,861,t,reaching=True,alarm=True,
                  emotion="knowing",gaze=-1)
        _blue_glass_key(d,890,956+int(5*math.sin(t*1.2)))
        _radio(d,254,1123,t,portable=True)
        _radio(d,868,1123,t,portable=True)
    elif action == "warn_parallel_cities":
        _dual_city_futures(d,state.event*3.1)
        performer(d,309,862,t,alarm=True)
        performer(d,515,866,t,reaching=True,alarm=True)
    elif action == "split_glass_key":
        _door(d,.57)
        mara=performer(d,280,867,t,reaching=True,alarm=True)
        double=performer(d,769,866,t,reaching=True,alarm=True,
                         emotion="knowing",gaze=-1)
        if state.event < .04:
            _blue_glass_key(d,540,930)
        else:
            # Separate the key, then transfer its two physical fragments
            # into Mara's right hand and the double's left hand.
            from astra_v2.human_prop_interaction import draw_split_key_in_hands
            draw_split_key_in_hands(d,state.event,
                                    mara["right_hand"],double["left_hand"])
        _radio(d,248,1145,t,portable=True)
        _radio(d,849,1145,t,portable=True)
    elif action == "seal_and_reveal_sea_door":
        _sealed_door_stars(d,state.attention*2.3)
        performer(d,298,868,t,reaching=True)
        if state.aftermath > .10:
            _notebook_sea_ending(d,t)
    else:
        raise CreativeReject("Unknown human action")
    return True
