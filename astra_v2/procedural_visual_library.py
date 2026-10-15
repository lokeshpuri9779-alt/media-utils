"""On-demand Pillow visual variants: 2,000 character skins and 2,000 icons.

These are reproducible *visual variants*, NOT 2,000 biological species, hand-
drawn SVG files or individual images. No downloads, secrets or paid models.
The eight supported characters retain species-specific silhouettes.
"""
from __future__ import annotations
import hashlib
import math
from PIL import ImageDraw

SPECIES = ("fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel")
PALETTES = (
    ((228,120,64),(58,158,164)), ((208,105,76),(117,116,187)),
    ((180,137,95),(64,123,156)), ((232,159,87),(149,102,134)),
    ((200,144,111),(86,151,117)), ((154,126,143),(207,115,117)),
    ((217,184,118),(74,136,171)), ((192,158,139),(160,113,183)),
    ((172,129,108),(67,163,156)), ((211,153,110),(175,127,103)),
)
COSTUMES = ("waistcoat", "hoodie", "explorer", "mechanic", "storybook")
ACCESSORIES = ("none", "scarf", "hat", "bow", "satchel")
CHARACTERS_PER_SPECIES = len(PALETTES)*len(COSTUMES)*len(ACCESSORIES)
CHARACTER_VARIANTS = len(SPECIES)*CHARACTERS_PER_SPECIES

MOTIFS = (
    "star","heart","leaf","moon","sun","flower","diamond","shield",
    "key","book","bell","lantern","clock","cloud","mountain",
    "compass","wrench","rocket","anchor","feather",
)
ICON_VARIANTS = len(MOTIFS)*10*10

def character_recipe(index):
    """Return a full art recipe, with bijective index 0..1999."""
    if not isinstance(index,int) or not 0 <= index < CHARACTER_VARIANTS:
        raise ValueError("character design index out of range")
    species_id, local = divmod(index, CHARACTERS_PER_SPECIES)
    palette_id, local = divmod(local, len(COSTUMES)*len(ACCESSORIES))
    costume_id, accessory_id = divmod(local, len(ACCESSORIES))
    fur, fabric=PALETTES[palette_id]
    return {"id": f"character-{index:04d}", "species": SPECIES[species_id],
            "palette": palette_id, "fur": fur, "fabric": fabric,
            "costume": COSTUMES[costume_id],
            "accessory": ACCESSORIES[accessory_id]}

def visual_identity(story, name, slot=0):
    """Use a story-level seed, NOT beat narration; clothes never flicker."""
    if name not in SPECIES:
        raise ValueError("unsupported actor")
    stable=str(story or "astra-default")
    seed=hashlib.sha256(f"{stable}|{name}|{slot}".encode()).digest()
    local=int.from_bytes(seed[:8],"big") % CHARACTERS_PER_SPECIES
    return SPECIES.index(name)*CHARACTERS_PER_SPECIES + local

def icon_recipe(index):
    if not isinstance(index,int) or not 0 <= index < ICON_VARIANTS:
        raise ValueError("icon recipe index out of range")
    motif_id, tail=divmod(index,100)
    palette, decoration=divmod(tail,10)
    return {"id":f"icon-{index:04d}", "motif":MOTIFS[motif_id],
            "palette":palette,"decoration":decoration}

def icon_for_story(motif, story, salt=""):
    if motif not in MOTIFS:
        raise ValueError("unknown motif")
    digest=hashlib.sha256(f"{story}|{motif}|{salt}".encode()).digest()
    local=int.from_bytes(digest[:8],"big")%100
    return MOTIFS.index(motif)*100 + local

def draw_costume_detail(d, x, y, recipe):
    """Additional recognisable costume geometry; stays inside subject bounds."""
    style=recipe["costume"]
    fabric=recipe["fabric"]
    ink=(35,43,56)
    if style=="hoodie":
        d.arc((x-78,y+84,x+78,y+223),180,355,fill=ink,width=11)
        d.line((x-17,y+145,x-17,y+207),fill=(242,231,211),width=5)
        d.line((x+17,y+145,x+17,y+207),fill=(242,231,211),width=5)
    elif style=="explorer":
        d.line((x-80,y+138,x+81,y+270),fill=(223,198,146),width=15)
        d.rounded_rectangle((x+37,y+197,x+82,y+243),radius=8,
                            fill=(187,154,99),outline=ink,width=3)
    elif style=="mechanic":
        d.rounded_rectangle((x-65,y+202,x-11,y+249),radius=6,
                            fill=(214,187,137),outline=ink,width=3)
        d.line((x-28,y+213,x-28,y+243),fill=fabric,width=7)
    elif style=="storybook":
        d.arc((x-95,y+89,x+95,y+255),15,160,fill=(235,209,155),width=11)
        d.ellipse((x-12,y+205,x+12,y+229),fill=(246,198,85))
    else:
        for yy in (186,235):
            d.ellipse((x-6,y+yy-6,x+6,y+yy+6),fill=(245,221,119),outline=ink,width=2)

def draw_accessory(d,x,y,recipe):
    a=recipe["accessory"]
    ink=(38,45,59)
    if a=="hat":
        d.polygon(((x-99,y-134),(x-77,y-199),(x+78,y-199),(x+100,y-134)),
                  fill=recipe["fabric"],outline=ink,width=5)
        d.rounded_rectangle((x-122,y-143,x+122,y-119),radius=9,
                            fill=recipe["fabric"],outline=ink,width=3)
    elif a=="scarf":
        d.arc((x-101,y+65,x+102,y+162),5,175,fill=(239,203,148),width=19)
        d.polygon(((x+74,y+118),(x+111,y+124),(x+97,y+249),(x+61,y+246)),
                  fill=(239,203,148))
    elif a=="bow":
        d.polygon(((x-8,y+114),(x-55,y+86),(x-55,y+143)),
                  fill=(241,206,134),outline=ink,width=3)
        d.polygon(((x+8,y+114),(x+55,y+86),(x+55,y+143)),
                  fill=(241,206,134),outline=ink,width=3)
        d.ellipse((x-13,y+105,x+13,y+126),fill=(207,137,98))
    elif a=="satchel":
        d.line((x-65,y+110,x+72,y+284),fill=(227,202,144),width=9)
        d.rounded_rectangle((x+48,y+240,x+106,y+294),radius=8,
                            fill=(159,113,78),outline=ink,width=4)

def _star(cx,cy,r,tips=5):
    return [(cx+int(r*(.47 if j%2 else 1)*math.cos(-math.pi/2+j*math.pi/tips)),
             cy+int(r*(.47 if j%2 else 1)*math.sin(-math.pi/2+j*math.pi/tips)))
            for j in range(tips*2)]

def draw_icon(d, index, x, y, size=48):
    """Render 20 different silhouettes and 10 palettes x 10 ornaments.

    Index is a visual STYLE ID, not a claim of 2,000 semantic icon concepts.
    No unrelated icon is substituted for a narrated object.
    """
    v=icon_recipe(index)
    motif, palette, deco = v["motif"],v["palette"],v["decoration"]
    colors=((239,190,100),(113,181,173),(197,134,179),(225,143,103),
            (155,180,222),(194,183,113),(147,204,150),(217,154,141),
            (192,155,217),(131,183,202))
    col=colors[palette]
    ink=(35,45,62)
    paper=(251,242,215)
    r=max(10,int(size*.46))
    def xy(dx,dy):
        return (round(x+dx*r),round(y+dy*r))
    def oval(ax,ay,bx,by,*,fill=col,outline=ink,width=3):
        a=xy(ax,ay); b=xy(bx,by)
        d.ellipse((*a,*b),fill=fill,outline=outline,width=width)
    def path(*points,fill=col,outline=ink,width=3):
        d.polygon([xy(*p) for p in points],fill=fill,outline=outline,width=width)
    def stroke(*points,fill=ink,width=4):
        d.line([xy(*p) for p in points],fill=fill,width=width,joint="curve")
    def rect(ax,ay,bx,by,fill=col,radius=.12):
        a=xy(ax,ay);b=xy(bx,by)
        d.rounded_rectangle((*a,*b),radius=max(2,int(radius*r)),
                            fill=fill,outline=ink,width=3)
    if motif=="star":
        d.polygon(_star(x,y,r,5),fill=col,outline=ink,width=3)
    elif motif=="sun":
        oval(-.49,-.49,.49,.49)
        for j in range(8):
            theta=j*math.pi/4
            stroke((.63*math.cos(theta),.63*math.sin(theta)),
                   (.94*math.cos(theta),.94*math.sin(theta)),width=4)
    elif motif=="flower":
        for j in range(6):
            theta=j*math.pi/3
            cx=.47*math.cos(theta);cy=.47*math.sin(theta)
            oval(cx-.33,cy-.33,cx+.33,cy+.33,fill=col,outline=ink,width=2)
        oval(-.25,-.25,.25,.25,fill=(248,221,121))
    elif motif=="compass":
        oval(-.91,-.91,.91,.91)
        path((0,-.81),(.24,0),(0,.81),(-.24,0),fill=paper)
        path((-.81,0),(0,-.24),(.81,0),(0,.24),fill=(226,132,112))
        oval(-.13,-.13,.13,.13,fill=ink,outline=ink)
    elif motif=="moon":
        oval(-.85,-.85,.85,.85)
        # A crescent whose inner cutout uses a consistent cutout fill.
        oval(-.25,-.98,1.0,.30,fill=(40,75,85),outline=(40,75,85),width=0)
    elif motif=="cloud":
        oval(-.94,-.16,-.29,.53,fill=col)
        oval(-.50,-.74,.31,.37,fill=col)
        oval(.12,-.38,.96,.53,fill=col)
        rect(-.77,.02,.78,.55,fill=col,radius=.16)
    elif motif=="heart":
        oval(-.86,-.72,.05,.16,fill=col)
        oval(-.05,-.72,.86,.16,fill=col)
        path((-.88,-.05),(.88,-.05),(0,.94))
    elif motif=="leaf":
        oval(-.70,-.82,.70,.82)
        stroke((-.62,.74),(.66,-.74),width=5)
        stroke((-.24,.22),(-.56,-.12),width=3)
        stroke((.15,-.15),(.52,.06),width=3)
    elif motif=="feather":
        oval(-.43,-.90,.53,.63)
        stroke((-.62,.93),(.40,-.77),width=5)
        for k in range(4):
            yy=.45-k*.32
            stroke((-.36,yy),(.26,yy-.20),width=2)
    elif motif=="diamond":
        path((-.66,-.28),(-.36,-.85),(.36,-.85),(.66,-.28),
             (0,.9))
        stroke((-.66,-.28),(.66,-.28),width=3)
        stroke((-.36,-.85),(0,.9),(.36,-.85),width=2)
    elif motif=="shield":
        path((-.83,-.80),(.83,-.80),(.70,.30),(0,.97),(-.70,.30))
        stroke((0,-.55),(0,.57),width=4)
        stroke((-.43,0),(.43,0),width=4)
    elif motif=="mountain":
        path((-.98,.85),(-.14,-.90),(.32,.14),(.55,-.37),
             (1,.85))
        path((-.47,-.13),(-.14,-.90),(.14,-.14),
             (-.12,-.30),fill=paper)
    elif motif=="rocket":
        path((0,-.99),(.47,-.47),(.41,.58),(-.41,.58),
             (-.47,-.47))
        oval(-.24,-.33,.24,.14,fill=(182,222,220))
        path((-.41,.20),(-.85,.76),(-.35,.59))
        path((.41,.20),(.85,.76),(.35,.59))
        path((-.25,.58),(0,1.05),(.25,.58),fill=(244,154,90))
    elif motif=="book":
        path((-.91,-.70),(-.16,-.62),(0,-.39),(0,.85),(-.91,.65))
        path((0,-.39),(.16,-.62),(.91,-.70),(.91,.65),(0,.85),fill=paper)
        stroke((0,-.39),(0,.85),width=4)
        for yy in (-.25,.12,.43):
            stroke((-.74,yy),(-.21,yy+.07),width=2)
    elif motif=="lantern":
        rect(-.65,-.61,.65,.80,fill=col,radius=.15)
        oval(-.32,-.93,.32,-.42,fill=None,outline=ink,width=5)
        rect(-.45,-.35,.45,.52,fill=(247,215,131),radius=.05)
        stroke((-.61,-.58),(.61,.77),width=3)
    elif motif=="clock":
        oval(-.88,-.88,.88,.88,fill=paper)
        stroke((0,0),(0,-.59),width=6)
        stroke((0,0),(.52,.27),width=5)
        oval(-.10,-.10,.10,.10,fill=ink,outline=ink)
    elif motif=="bell":
        path((-.76,.57),(-.62,.35),(-.56,-.33),(-.28,-.67),
             (.28,-.67),(.56,-.33),(.62,.35),(.76,.57))
        oval(-.20,.56,.20,.89,fill=(244,178,116))
        stroke((-.83,.59),(.83,.59),width=5)
    elif motif=="key":
        oval(-.90,-.76,-.13,.04,fill=paper)
        stroke((-.24,-.13),(.82,.86),width=9)
        stroke((.51,.55),(.83,.20),width=7)
        stroke((.68,.74),(.95,.44),width=7)
    elif motif=="wrench":
        path((-.91,-.80),(-.58,-.96),(-.19,-.45),
             (.07,-.37),(.78,.55),(.49,.84),(-.42,.06),
             (-.61,-.02),(-.97,-.48),fill=col)
        oval(.35,.42,.61,.68,fill=paper)
    elif motif=="anchor":
        oval(-.19,-.92,.19,-.56,fill=paper)
        stroke((0,-.55),(0,.80),width=8)
        stroke((-.57,-.17),(.57,-.17),width=7)
        d.arc((*xy(-.83,.10),*xy(.83,.90)),0,180,fill=ink,width=7)
        stroke((-.86,.38),(-.73,.86),width=6)
        stroke((.86,.38),(.73,.86),width=6)
    else:
        raise ValueError("unknown motif recipe")
    # Distinct decoration geometry within each motif; bounded and stable.
    if deco:
        for k in range(1+(deco-1)//3):
            ax=-.85+((k*17+deco*13)%160)/100
            ay=.83-(k*19+deco*7)%47/100
            px,py=xy(ax,ay)
            rad=2+deco%3
            d.ellipse((px-rad,py-rad,px+rad,py+rad),fill=(255,239,206))
    return v["id"]
