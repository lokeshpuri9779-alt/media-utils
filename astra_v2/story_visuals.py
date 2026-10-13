"""Story-specific illustrated subjects for free CPU rendering.

Draws a distinct subject from the actual narration rather than reusing the
generic robot/door icons for unrelated fiction.
"""
import math
import re
from PIL import ImageDraw

SUBJECTS = (
    ("fox", r"\bfox\b|\bfoxes\b"),
    ("owl", r"\bowl\b|\bowls\b"),
    ("duck", r"\bduck\b|\bgoose\b|\bgeese\b"),
    ("squirrel", r"\bsquirrel\b|\bchipmunk\b"),
    ("mouse", r"\bmouse\b|\bmice\b|\bmole\b"),
    ("otter", r"\botter\b|\bbeaver\b"),
    ("crab", r"\bcrab\b"),
    ("firefly", r"\bfirefl\w*\b"),
    ("cat", r"\bcat\b|\bfeline\b|\bkitten\b"),
    ("dog", r"\bdog\b|\bpuppy\b|\bhound\b"),
    ("monkey", r"\bmonkey\b|\bape\b|\bbaboon\b"),
    ("bird", r"\bbird\b|\bparrot\b|\bsparrow\b|\bcrow\b|\bpigeon\b"),
    ("rabbit", r"\brabbit\b|\bbunny\b|\bhare\b"),
    ("book", r"\bbook\b|\blibrar\w*|\bpages\b|\bnewspaper\b"),
    ("ocean", r"\bocean\b|\bunderwater\b|\bfish\b|\bjellyfish\b|\bcoral\b"),
    ("clock", r"\bclock\b|\btimepiece\b|\bclocktower\b"),
    ("museum", r"\bmuseum\b|\bexhibit\b|\bartifact\b"),
    ("whale", r"\bwhale\b"),
    ("tree", r"\bforest\b|\btree\b|\bseed\b"),
    ("train", r"\btrain\b|\brailway\b"),
    ("moon", r"\bmoon\b|\blunar\b"),
    ("robot", r"\brobot\b|\bmachine\b"),
)

def select_subject(story, shot):
    local = " ".join(str(shot.get(k) or "") for k in ("speech", "visual_prompt", "visual", "action", "headline", "label")).lower()
    global_text = " ".join(str(story.get(k) or "") for k in ("title", "question", "answer")).lower()
    # A shot should depict the subject mentioned in that shot, not the first
    # matching word from the entire episode or the fixed subject catalog.
    # Prefer the earliest mention when several objects appear in one beat.
    for text in (local,):
        matches = [(match.start(), name)
                   for name, pattern in SUBJECTS
                   if (match := re.search(pattern, text))]
        if matches:
            return min(matches, key=lambda item: item[0])[1]
    # A title-level subject is appropriate only when the beat supplies no
    # distinct visual direction. Otherwise it makes every shot repeat the
    # same illustration even when the storyboard changes locations/actions.
    explicit_visual = str(shot.get("visual_prompt") or shot.get("visual") or "").strip().lower()
    generic_visuals = {"", "story", "illustration", "fiction", "subject"}
    if explicit_visual not in generic_visuals:
        return None
    matches = [(match.start(), name)
               for name, pattern in SUBJECTS
               if (match := re.search(pattern, global_text))]
    return min(matches, key=lambda item: item[0])[1] if matches else None


def draw_subject(image, subject, t, accent):
    """Return True when a bespoke subject was drawn; False for unknown subjects."""
    if subject not in {x[0] for x in SUBJECTS}:
        return False
    # New story characters use the closest existing animated silhouette until
    # dedicated drawings are available; do not fall back to generic icons.
    subject = {"fox": "dog", "otter": "dog", "owl": "bird",
               "duck": "bird", "firefly": "bird", "squirrel": "rabbit",
               "mouse": "rabbit", "crab": "ocean"}.get(subject, subject)
    d = ImageDraw.Draw(image)
    cx, cy = 520, 850
    # Subject-specific moving scenery behind the central character.
    if subject in ("cat", "clock"):
        for i in range(5):
            x = 130 + i*200 + int(15*math.sin(t*.8+i))
            d.ellipse((x-52, 520, x+52, 625), outline=(139,115,88), width=9)
            d.line((x,620,x,1170), fill=(76,62,76), width=12)
    elif subject in ("book", "museum"):
        for i in range(5):
            x = 95+i*205
            d.rectangle((x,560,x+125,1210), outline=(108,76,103), width=12)
            for j in range(4):
                y = 650+j*120+int(6*math.sin(t+i+j))
                d.line((x+12,y,x+112,y), fill=(164,126,111), width=9)
    elif subject in ("ocean", "whale"):
        for i in range(18):
            x = 110+(i*71)%850
            y = 580+(i*83)%580-int((t*24+i*3)%140)
            r = 5+(i%4)*3
            d.ellipse((x-r,y-r,x+r,y+r), outline=(107,189,222), width=3)
    else:
        for i in range(15):
            x = 120+(i*79)%830+int(12*math.sin(t*.4+i))
            y = 520+(i*61)%650
            r = 2+(i%3)*2
            d.ellipse((x-r,y-r,x+r,y+r), fill=(109,138,168))
    sway = int(math.sin(t * 1.7) * 14)
    if subject == "cat":
        x = cx + sway
        # Animated tail, attentive ear tilt and intermittent blinking make the
        # character read as alive without changing the CPU drawing pipeline.
        tail = int(95 * math.sin(t * 2.2))
        d.arc((x+95, 790-tail//3, x+315, 1100+tail//3),
              205, 355, fill=(205, 125, 65), width=26)
        d.ellipse((x-155, 740, x+155, 1050), fill=(205, 125, 65), outline=(255, 198, 115), width=7)
        d.polygon([(x-140, 785), (x-120, 600), (x-20, 735)], fill=(205, 125, 65))
        d.polygon([(x+140, 785), (x+120, 600), (x+20, 735)], fill=(205, 125, 65))
        blink = abs(math.sin(t * 1.15 + 0.6)) > 0.985
        for dx in (-70, 70):
            if blink:
                d.line((x+dx-22, 875, x+dx+22, 875), fill=(30, 42, 45), width=8)
            else:
                d.ellipse((x+dx-22, 850, x+dx+22, 900), fill=(30, 42, 45))
        d.polygon([(x-18, 938), (x+18, 938), (x, 960)], fill=(255, 185, 190))
        d.arc((x-55, 955, x+55, 990), 0, 180, fill=(35, 38, 44), width=5)
    elif subject == "rabbit":
        x = cx + int(36 * math.sin(t * 1.8))
        y = 860 - int(34 * abs(math.sin(t * 2.8)))
        fur = (228, 207, 186)
        d.ellipse((x-135, y+40, x+135, y+285), fill=fur)
        d.ellipse((x-130, y-150, x+130, y+100), fill=fur)
        for dx in (-75, 75):
            tilt = int(15 * math.sin(t * 2.0 + dx))
            d.ellipse((x+dx-35+tilt, y-390, x+dx+35+tilt, y-95),
                      fill=fur, outline=(180, 150, 140), width=5)
            d.ellipse((x+dx-17+tilt, y-365, x+dx+17+tilt, y-115),
                      fill=(229, 153, 164))
        for dx in (-55, 55):
            d.ellipse((x+dx-14, y-65, x+dx+14, y-35),
                      fill=(40, 42, 47))
        d.ellipse((x-18, y+5, x+18, y+30), fill=(217, 124, 140))
        d.arc((x-45, y+10, x+45, y+75), 10, 170,
              fill=(112, 83, 80), width=5)
    elif subject == "bird":
        x = cx + int(75 * math.sin(t * 1.3))
        y = 820 + int(55 * math.sin(t * 2.1))
        wing = int(95 * math.sin(t * 7.0))
        d.ellipse((x-125, y-80, x+125, y+125),
                  fill=(63, 160, 166), outline=(132, 220, 207), width=7)
        d.polygon([(x-45, y+5), (x-220, y-85-wing),
                   (x-160, y+100)], fill=(37, 117, 150))
        d.polygon([(x+45, y+5), (x+220, y-85-wing),
                   (x+160, y+100)], fill=(37, 117, 150))
        for dx in (-55, 55):
            d.ellipse((x+dx-15, y-45, x+dx+15, y-15), fill=(24, 39, 47))
        d.polygon([(x-24, y+7), (x+24, y+7), (x, y+55)],
                  fill=(246, 177, 72))
    elif subject in ("dog", "monkey"):
        x = cx + sway
        bob = int(15 * abs(math.sin(t * 2.5)))
        y = 840 - bob
        fur = (196, 135, 79) if subject == "dog" else (148, 101, 70)
        d.arc((x+100, y+20, x+260+int(30*math.sin(t*3)), y+240),
              190, 350, fill=fur, width=22)
        d.ellipse((x-130, y+60, x+130, y+300), fill=fur)
        # Alternating footfall with a slight phase offset: the legs actually
        # step rather than the entire character only bobbing in place.
        stride = math.sin(t * 5.2)
        for side, dx in enumerate((-75, 75)):
            step = int(35 * stride * (1 if side == 0 else -1))
            lift = int(25 * max(0.0, stride * (1 if side == 0 else -1)))
            d.rounded_rectangle((x+dx-30+step, y+260-lift,
                                 x+dx+30+step, y+365-lift),
                                radius=20, fill=fur)
        d.ellipse((x-155, y-180, x+155, y+115), fill=fur)
        for dx in (-135, 135):
            d.ellipse((x+dx-42, y-120, x+dx+42, y+25),
                      fill=(117, 76, 55))
        if subject == "monkey":
            d.ellipse((x-105, y-95, x+105, y+100), fill=(218, 172, 126))
        blink = abs(math.sin(t * 1.4)) > 0.985
        for dx in (-65, 65):
            if blink:
                d.line((x+dx-18, y-35, x+dx+18, y-35),
                       fill=(35, 30, 32), width=7)
            else:
                d.ellipse((x+dx-15, y-55, x+dx+15, y-15),
                          fill=(35, 30, 32))
        d.ellipse((x-22, y+12, x+22, y+42), fill=(48, 35, 36))
        d.arc((x-48, y+18, x+48, y+85), 5, 175,
              fill=(60, 40, 42), width=6)

    elif subject == "book":
        x = cx + sway
        d.rounded_rectangle((x-260, 650, x+260, 1080), radius=20,
                            fill=(103, 59, 78), outline=accent, width=9)
        d.polygon([(x, 690), (x-220, 720), (x-220, 1020), (x, 990)],
                  fill=(244, 223, 181))
        d.polygon([(x, 690), (x+220, 720), (x+220, 1020), (x, 990)],
                  fill=(228, 208, 171))
        # A page visibly turns rather than leaving the illustrated book static.
        flip = (math.sin(t * 1.4) + 1.0) / 2.0
        page_edge = x + int(205 * (1.0 - 2.0 * flip))
        d.polygon([(x, 690), (page_edge, 720), (page_edge, 1020), (x, 990)],
                  fill=(252, 235, 200))
        d.line((x, 690, x, 990), fill=(125, 92, 70), width=6)
        for y in (785, 845, 905):
            d.line((x-185, y, x-45, y+5), fill=(151, 125, 100), width=4)
            d.line((x+45, y+5, x+185, y), fill=(151, 125, 100), width=4)
    elif subject in ("ocean", "whale"):
        for i in range(5):
            y = 675+i*105
            pts = [(x, y+int(18*math.sin(x*.018+t+i))) for x in range(130, 920, 16)]
            d.line(pts, fill=(40+i*8, 140+i*10, 210+i*6), width=9)
        if subject == "whale":
            x = cx + int(math.sin(t) * 60)
            d.ellipse((x-225, 800, x+180, 990), fill=(79, 155, 185))
            d.polygon([(x+155, 890), (x+300, 810), (x+300, 990)], fill=(79, 155, 185))
            d.ellipse((x-145, 855, x-125, 875), fill=(8, 24, 40))
        else:
            # Ocean-only stories should not silently acquire a whale character.
            for i in range(4):
                x = 240 + i * 170 + int(24 * math.sin(t * 0.7 + i))
                y = 850 + (i % 2) * 110 + int(12 * math.sin(t + i))
                d.polygon([(x-35, y), (x+35, y-25), (x+35, y+25)],
                          fill=(88, 205, 201))
                d.polygon([(x+35, y), (x+70, y-30), (x+70, y+30)],
                          fill=(66, 162, 179))
    elif subject == "clock":
        d.ellipse((cx-245, 625, cx+245, 1115), fill=(95, 66, 54), outline=(240, 195, 115), width=18)
        d.ellipse((cx-195, 675, cx+195, 1065), fill=(32, 38, 58), outline=accent, width=5)
        a=t*.5
        d.line((cx, 870, cx+int(math.sin(a)*135), 870-int(math.cos(a)*135)), fill=(245, 235, 211), width=12)
        d.line((cx, 870, cx+int(math.sin(a*.16)*90), 870-int(math.cos(a*.16)*90)), fill=accent, width=17)
    elif subject == "tree":
        # Wind bends the trunk and moves entire canopy clusters, not just stars.
        bend = int(34 * math.sin(t * 1.7))
        d.polygon([(cx-70, 1120), (cx-45+bend//2, 790),
                   (cx+50+bend//2, 790), (cx+85, 1120)], fill=(120, 82, 54))
        for j, (x, y, r) in enumerate(((cx-135, 790, 145),
                                       (cx+130, 790, 155), (cx, 670, 190))):
            sway = int((35+j*9) * math.sin(t*1.7+j*.2))
            d.ellipse((x-r+sway, y-r, x+r+sway, y+r),
                      fill=(45, 132, 96), outline=(85, 177, 120), width=7)
        for j in range(35):
            phase = t*1.7+j*.67
            x = cx-240+(j*97)%480+int(32*math.sin(phase))
            y = 550+(j*71)%410+int(28*math.cos(phase))
            d.ellipse((x-7, y-5, x+7, y+5), fill=(110, 198, 117))
    elif subject == "train":
        # Tracks and sleepers scroll independently from the locomotive.
        # Unlike a fixed train card, the motion reads as forward travel.
        track_y = 1125
        d.line((95, track_y, 970, track_y), fill=(151, 154, 166), width=12)
        d.line((95, track_y+78, 970, track_y+78), fill=(151, 154, 166), width=12)
        offset = int(t * 95) % 120
        for sleeper in range(-1, 10):
            sx = 95 + sleeper * 120 - offset
            d.line((sx, track_y-12, sx+30, track_y+93),
                   fill=(101, 83, 79), width=17)
        x=cx+int(10*math.sin(t*2.5))
        y_shift=int(5*math.sin(t*8))
        d.rounded_rectangle((x-230, 690+y_shift, x+230, 1080+y_shift),
                            radius=45, fill=(100, 105, 156), outline=accent, width=9)
        d.rectangle((x-160, 740+y_shift, x+160, 900+y_shift), fill=(42, 69, 91))
        for dx in (-135,135):
            d.ellipse((x+dx-45, 1020+y_shift, x+dx+45, 1110+y_shift),
                      fill=(35, 41, 57), outline=accent, width=6)
            hub_x=x+dx
            angle=t*7
            d.line((hub_x, 1065+y_shift,
                    hub_x+int(30*math.cos(angle)), 1065+y_shift+int(30*math.sin(angle))),
                   fill=(194, 199, 211), width=6)
    elif subject == "moon":
        d.ellipse((cx-240+sway, 620, cx+240+sway, 1100), fill=(215, 207, 177), outline=accent, width=8)
        for dx,dy,r in ((-85,-85,46),(110,50,65),(-45,115,33)):
            x=cx+dx+sway; y=860+dy
            d.ellipse((x-r,y-r,x+r,y+r), fill=(171, 163, 149))
    else:
        x=cx+sway
        d.rounded_rectangle((x-150, 720, x+150, 980), radius=50, fill=(91, 119, 139), outline=accent, width=8)
        d.rounded_rectangle((x-105, 795, x+105, 885), radius=20, fill=(25, 36, 55))
        for dx in (-50,50):
            d.ellipse((x+dx-15, 820, x+dx+15, 850), fill=accent)
    return True
