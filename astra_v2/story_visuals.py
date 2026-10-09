"""Story-specific illustrated subjects for free CPU rendering.

Draws a distinct subject from the actual narration rather than reusing the
generic robot/door icons for unrelated fiction.
"""
import math
import re
from PIL import ImageDraw

SUBJECTS = (
    ("cat", r"\bcat\b|\bfeline\b|\bkitten\b"),
    ("book", r"\bbook\b|\blibrar\w*|\bpages\b|\bnewspaper\b"),
    ("ocean", r"\bocean\b|\bunderwater\b|\bfish\b|\bjellyfish\b|\bcoral\b"),
    ("clock", r"\bclock\b|\btimepiece\b|\bclocktower\b"),
    ("museum", r"\bmuseum\b|\bexhibit\b|\bartifact\b"),
    ("whale", r"\bwhale\b"),
    ("tree", r"\bforest\b|\btree\b|\bseed\b|\bfirefl\w*"),
    ("train", r"\btrain\b|\brailway\b"),
    ("moon", r"\bmoon\b|\blunar\b"),
    ("robot", r"\brobot\b|\bmachine\b"),
)

def select_subject(story, shot):
    local = " ".join(str(shot.get(k) or "") for k in ("speech", "headline", "label")).lower()
    global_text = " ".join(str(story.get(k) or "") for k in ("title", "question", "answer")).lower()
    for text in (local, global_text):
        for name, pattern in SUBJECTS:
            if re.search(pattern, text):
                return name
    return None


def draw_subject(image, subject, t, accent):
    """Return True when a bespoke subject was drawn; False for unknown subjects."""
    if subject not in {x[0] for x in SUBJECTS}:
        return False
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
        d.ellipse((x-155, 740, x+155, 1050), fill=(205, 125, 65), outline=(255, 198, 115), width=7)
        d.polygon([(x-140, 785), (x-120, 600), (x-20, 735)], fill=(205, 125, 65))
        d.polygon([(x+140, 785), (x+120, 600), (x+20, 735)], fill=(205, 125, 65))
        for dx in (-70, 70):
            d.ellipse((x+dx-22, 850, x+dx+22, 900), fill=(30, 42, 45))
        d.polygon([(x-18, 938), (x+18, 938), (x, 960)], fill=(255, 185, 190))
        d.arc((x-55, 955, x+55, 990), 0, 180, fill=(35, 38, 44), width=5)
    elif subject in ("book", "museum"):
        x = cx+sway
        d.rounded_rectangle((x-260, 650, x+260, 1080), radius=20, fill=(103, 59, 78), outline=accent, width=9)
        d.polygon([(x, 690), (x-220, 720), (x-220, 1020), (x, 990)], fill=(244, 223, 181))
        d.polygon([(x, 690), (x+220, 720), (x+220, 1020), (x, 990)], fill=(228, 208, 171))
        d.line((x, 690, x, 990), fill=(125, 92, 70), width=6)
        for y in (785, 845, 905):
            d.line((x-185, y, x-45, y+5), fill=(151, 125, 100), width=4)
            d.line((x+45, y+5, x+185, y), fill=(151, 125, 100), width=4)
    elif subject in ("ocean", "whale"):
        for i in range(5):
            y = 675+i*105
            pts = [(x, y+int(18*math.sin(x*.018+t+i))) for x in range(130, 920, 16)]
            d.line(pts, fill=(40+i*8, 140+i*10, 210+i*6), width=9)
        x=cx+int(math.sin(t)*60)
        d.ellipse((x-225, 800, x+180, 990), fill=(79, 155, 185))
        d.polygon([(x+155, 890), (x+300, 810), (x+300, 990)], fill=(79, 155, 185))
        d.ellipse((x-145, 855, x-125, 875), fill=(8, 24, 40))
    elif subject == "clock":
        d.ellipse((cx-245, 625, cx+245, 1115), fill=(95, 66, 54), outline=(240, 195, 115), width=18)
        d.ellipse((cx-195, 675, cx+195, 1065), fill=(32, 38, 58), outline=accent, width=5)
        a=t*.5
        d.line((cx, 870, cx+int(math.sin(a)*135), 870-int(math.cos(a)*135)), fill=(245, 235, 211), width=12)
        d.line((cx, 870, cx+int(math.sin(a*.16)*90), 870-int(math.cos(a*.16)*90)), fill=accent, width=17)
    elif subject == "tree":
        d.polygon([(cx-70, 1120), (cx-45, 790), (cx+50, 790), (cx+85, 1120)], fill=(120, 82, 54))
        for x,y,r in ((cx-135,790,145),(cx+130,790,155),(cx,670,190)):
            d.ellipse((x-r,y-r,x+r,y+r), fill=(45, 132, 96), outline=(85, 177, 120), width=7)
    elif subject == "train":
        x=cx+sway
        d.rounded_rectangle((x-230, 690, x+230, 1080), radius=45, fill=(100, 105, 156), outline=accent, width=9)
        d.rectangle((x-160, 740, x+160, 900), fill=(42, 69, 91))
        for dx in (-135,135):
            d.ellipse((x+dx-45, 1020, x+dx+45, 1110), fill=(35, 41, 57), outline=accent, width=6)
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
