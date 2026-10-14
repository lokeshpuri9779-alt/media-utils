"""Recognizable procedural icons for selected world items.

Specific shape adapters override the generic category renderer. Unsupported
items fall back to the existing category prototype; no false coverage claim.
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from experimental.world_renderer import draw_asset

SUPPORTED = {
 "apple","banana","orange","grape","strawberry","mango",
 "sun","moon","star","cloud","house","shoe","hat","glasses","watch",
 "shirt","jacket","backpack","umbrella","flower"
}

def render_item(kind: str, category: str, seed: str="demo", size: int=192) -> Image.Image:
    if size<32: raise ValueError("size must be >= 32")
    if kind not in SUPPORTED:
        return draw_asset(category,seed,size=size)
    im=Image.new("RGB",(size,size),(238,243,248))
    d=ImageDraw.Draw(im)
    s=size/192
    def ell(b,c): d.ellipse(tuple(round(v*s) for v in b),fill=c)
    def rec(b,c): d.rectangle(tuple(round(v*s) for v in b),fill=c)
    def poly(pts,c): d.polygon([(round(x*s),round(y*s)) for x,y in pts],fill=c)
    def line(pts,c,w=5): d.line([(round(x*s),round(y*s)) for x,y in pts],fill=c,width=max(1,round(w*s)))
    if kind=="sun":
        for a in range(0,360,45):
            import math
            x,y=96+68*math.cos(math.radians(a)),96+68*math.sin(math.radians(a))
            x2,y2=96+83*math.cos(math.radians(a)),96+83*math.sin(math.radians(a))
            line([(x,y),(x2,y2)],(239,166,53),7)
        ell((48,48,144,144),(250,206,73))
    elif kind=="moon":
        ell((40,34,151,153),(235,221,158))
        ell((76,20,171,122),(238,243,248))
    elif kind=="star":
        import math
        pts=[]
        for i in range(10):
            a=-math.pi/2+i*math.pi/5
            r=75 if i%2==0 else 32
            pts.append((96+r*math.cos(a),96+r*math.sin(a)))
        poly(pts,(245,200,79))
    elif kind=="cloud":
        for b in ((35,88,105,145),(65,53,134,137),(107,85,169,144)):
            ell(b,(245,248,250))
        rec((54,109,149,144),(245,248,250))
        line([(45,145),(157,145)],(164,182,200),3)
    elif kind in ("apple","orange","mango"):
        color={"apple":(213,72,71),"orange":(242,158,55),"mango":(245,189,63)}[kind]
        ell((50,60,144,155),color)
        line([(96,67),(102,45)],(106,84,52),7)
        ell((104,48,136,64),(74,153,78))
    elif kind=="banana":
        poly([(43,74),(57,128),(95,153),(135,131),(154,91),(132,113),(96,125),(68,109)],(245,213,91))
        line([(43,74),(57,128),(95,153),(135,131)],(181,140,52),3)
    elif kind=="grape":
        for x,y in ((79,76),(109,76),(65,101),(95,102),(123,102),(79,128),(109,128),(95,151)):
            ell((x-16,y-16,x+16,y+16),(139,90,176))
        line([(94,62),(101,42)],(84,132,75),6)
    elif kind=="strawberry":
        poly([(53,75),(140,75),(129,126),(97,158),(65,126)],(217,69,79))
        poly([(61,78),(79,58),(97,76),(114,58),(133,78)],(71,152,79))
        for x,y in ((81,101),(109,105),(96,126)):
            ell((x-3,y-4,x+3,y+4),(249,218,139))
    elif kind=="house":
        rec((47,82,148,162),(225,168,112))
        poly([(34,86),(98,32),(162,86)],(150,86,78))
        rec((85,115,112,162),(112,76,61))
        rec((55,99,75,122),(181,218,233))
    elif kind=="shoe":
        poly([(35,119),(75,112),(96,85),(122,99),(133,120),(166,131),(168,151),(36,151)],(77,117,180))
        rec((37,145,166,156),(243,242,234))
        for x in (91,105,119):
            line([(x,107),(x+8,113)],(244,246,248),3)
    elif kind=="hat":
        ell((51,63,143,133),(98,132,191))
        rec((35,123,158,137),(74,106,163))
    elif kind=="glasses":
        for x in (46,112):
            ell((x,78,x+42,119),(63,70,80))
            ell((x+6,84,x+36,113),(201,225,237))
        line([(88,95),(112,95)],(63,70,80),5)
    elif kind=="watch":
        rec((80,32,113,161),(80,113,149))
        ell((62,65,131,134),(49,60,73))
        ell((70,73,123,126),(219,229,237))
        line([(96,99),(96,81)],(51,63,76),4)
        line([(96,99),(112,109)],(51,63,76),4)
    elif kind in ("shirt","jacket"):
        color=(96,162,200) if kind=="shirt" else (177,99,124)
        poly([(63,54),(82,43),(110,43),(130,54),(158,85),(138,106),(127,94),(127,160),(65,160),(65,94),(53,106),(33,85)],color)
        if kind=="jacket":
            line([(96,52),(96,158)],(235,225,217),5)
    elif kind=="backpack":
        ell((57,52,138,161),(112,116,181))
        rec((71,108,123,144),(80,86,146))
        line([(70,66),(70,43),(120,43),(120,66)],(58,67,105),8)
    elif kind=="umbrella":
        ell((37,42,156,120),(219,91,107))
        rec((37,99,156,119),(238,243,248))
        line([(96,111),(96,161),(115,161)],(83,89,99),6)
    elif kind=="flower":
        for x,y in ((96,59),(65,89),(127,89),(77,120),(115,120)):
            ell((x-22,y-22,x+22,y+22),(231,124,161))
        ell((81,77,111,107),(239,201,74))
        line([(96,109),(96,168)],(76,147,84),7)
    return im
