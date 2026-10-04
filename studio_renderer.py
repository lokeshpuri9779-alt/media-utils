"""Astra Studio: original motion graphics, local neural voice and timed sound.

No paid APIs, stock clips or copied soundtrack. Kokoro-82M model: Apache-2.0;
kokoro-onnx: MIT. Model files are downloaded to the runner cache, never to git.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
# Disable ONNX telemetry before any import can initialize its native runtime.
os.environ['ORT_DISABLE_TELEMETRY'] = '1'
from pathlib import Path
import re
import subprocess
import tempfile
import wave
from functools import lru_cache

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from imageio_ffmpeg import get_ffmpeg_exe

VERSION = "studio-1.0"
W, H, FPS, RATE = 1080, 1920, 30, 24000
ASSET_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
MODEL_FILES = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
THEMES = {
    "space": ((7, 10, 27), (35, 21, 59), (255, 174, 91)),
    "football": ((3, 21, 24), (4, 45, 44), (131, 255, 178)),
    "tech": ((8, 16, 32), (17, 41, 69), (85, 220, 255)),
    "fiction": ((8, 11, 28), (32, 18, 48), (188, 163, 255)),
    "challenge": ((15, 10, 28), (37, 18, 64), (227, 252, 107)),
}


@lru_cache(maxsize=128)
def font(size, regular=False):
    name = 'DejaVuSans.ttf' if regular else 'DejaVuSans-Bold.ttf'
    for root in ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu'):
        path = Path(root) / name
        if path.exists():
            return ImageFont.truetype(str(path), int(size))
    raise RuntimeError('DejaVu fonts are required for Studio rendering.')


def ease(v):
    v = max(0.0, min(1.0, v))
    return 1 - (1-v)**3


def fit_text(draw, text, box, size=90, fill='white', align='center', max_lines=4):
    """Wrap to measured pixels and shrink to the complete box, including height."""
    x0, y0, x1, y1 = box
    for n in range(size, 21, -2):
        f = font(n)
        lines = []
        for para in str(text).split('\n'):
            line = ''
            for word in para.split():
                nxt = (line + ' ' + word).strip()
                if draw.textlength(nxt, font=f) > x1-x0 and line:
                    lines.append(line)
                    line = word
                else:
                    line = nxt
            lines.append(line)
        result = '\n'.join(lines)
        bb = draw.multiline_textbbox((0,0), result, font=f, spacing=int(n*.16))
        if len(lines) <= max_lines and bb[2]-bb[0] <= x1-x0 and bb[3]-bb[1] <= y1-y0:
            draw.multiline_text(((x0+x1)/2, (y0+y1)/2), result, font=f,
                                fill=fill, anchor='mm', align=align, spacing=int(n*.16))
            return
    raise ValueError('Text cannot fit safely: '+str(text)[:60])


def scene(headline, speech, visual, label='', sub='', duration=0, **extra):
    return dict(headline=headline, speech=speech, visual=visual, label=label,
                sub=sub, min_duration=duration, **extra)


def make_plan(ch):
    genre, cid = ch.get('genre', 'challenge'), ch.get('content_id', '')
    q, a = ch['question'].replace('\n', ' '), ch['answer'].replace('\n', ' ')
    if cid == 'venus-spin':
        return [
            scene('ONE SPIN\nLONGER THAN A YEAR', 'On Venus, one spin takes longer than a year.', 'planet', 'VENUS', 'THE CLOCK RUNS DIFFERENTLY'),
            scene('ONE ROTATION', 'Venus needs about two hundred forty-three Earth days to rotate once.', 'planet', '243', 'EARTH DAYS', rotation=True),
            scene('ONE ORBIT', 'But its orbit takes only about two hundred twenty-five Earth days.', 'orbit', '225', 'EARTH DAYS'),
            scene('THE YEAR WINS', 'A whole year ends before one rotation is finished.', 'compare', '243 > 225', 'ROTATION  /  ORBIT'),
        ]
    if cid == 'venus-heat':
        return [scene('THE HOTTEST PLANET?', 'The hottest planet is not Mercury.', 'orbit', 'NOT MERCURY', 'CLOSER DOES NOT ALWAYS MEAN HOTTER'),
                scene('IT IS VENUS', 'It is Venus. Its thick atmosphere traps heat.', 'planet', 'VENUS', 'A THICK ATMOSPHERE', hot=True),
                scene('HEAT GETS TRAPPED', 'That powerful greenhouse effect makes Venus hotter than any other planet.', 'planet', 'GREENHOUSE', 'ENERGY IN. HEAT TRAPPED.', hot=True)]
    if genre == 'tech':
        keys = {'clipboard':['WIN','V'], 'screenshot':['WIN','SHIFT','S'], 'taskmanager':['CTRL','SHIFT','ESC']}.get(cid,['WIN'])
        spoken = {'clipboard':'Press the Windows key and V. Enable clipboard history first.',
                  'screenshot':'Press Windows, Shift, and S. Then select the area you want.',
                  'taskmanager':'Press Control, Shift, and Escape. Check the Processes tab.'}.get(cid,a)
        payoff = {'clipboard':('YOUR RECENT COPIES','Keep sensitive information out of clipboard history.'),
                  'screenshot':('JUST THE PART YOU NEED','You now have a screenshot of just that area.'),
                  'taskmanager':('SEE WHAT IS BUSY','See which apps are using your computer resources.')}.get(cid,('TRY IT',a))
        return [scene(ch['hook'],q,'screen','WINDOWS','A SHORTCUT WORTH KNOWING',tool=cid),
                scene('THE SHORTCUT',spoken,'keys',' + '.join(keys),'TRY IT ON YOUR KEYBOARD',keys=keys),
                scene(payoff[0],payoff[1],'screen','DONE','SAVE THE SHORTCUT',tool=cid,reveal=True)]
    if genre == 'football':
        heads={'offside-position':('POSITION ≠ OFFENCE','INVOLVEMENT MATTERS'),
               'throw-offside':('DIRECT FROM A THROW-IN?','NO OFFSIDE OFFENCE'),
               'added-time':('THE BOARD SAYS +5','FIVE IS THE MINIMUM')}
        first,last=heads.get(cid,(ch['hook'],'THE RULE'))
        speech = a.replace('Law 11','Law eleven')
        return [scene(first,q,'pitch','THE SITUATION','FOOTBALL, EXPLAINED',rule=cid),
                scene(last,speech,'pitch','THE RULE','ILLUSTRATION',rule=cid,reveal=True),
                scene('NOW YOU KNOW', 'Small details change how the rule works.', 'pitch','DETAILS MATTER','SOURCE: IFAB',rule=cid,reveal=True)]
    if genre == 'fiction':
        # Explicit fiction label remains visible for the complete video.
        beats = {
            'last-signal': [('THE LAST SIGNAL','The empty spaceship received one message.','ship','INCOMING SIGNAL'),
                           ('STOP LOOKING FOR US','Stop looking for us.','signal','TRANSMISSION RECEIVED'),
                           ('SENT FROM EARTH','The sender was Earth.','planet','EARTH'),
                           ('EARTH WAS GONE','But Earth had vanished a hundred years ago.','signal','100 YEARS TOO LATE')],
            'door':[('THE EXTRA DOOR','Every night, another door appeared in her tiny flat.','door','NIGHT 01'),
                    ('SHE OPENED ONE','Tonight, she finally opened one.','door','DO NOT KNOCK'),
                    ('SOMEONE WAS THERE','On the other side, someone was knocking.','door','WHO IS OUTSIDE?'),
                    ('IT WAS HER','It was her.','door','THE OTHER SIDE')],
            'robot':[('ONE LAST ORDER','The old robot had one last order.','robot','PROTECT THE SEED'),
                     ('KEEP IT SAFE','Guard a single seed.','robot','DAY 01'),
                     ('A THOUSAND YEARS','A thousand years later, it finally rested.','forest','YEAR 1000'),
                     ('MISSION COMPLETE','In the shade of a forest.','forest','MISSION COMPLETE')],
        }.get(cid,[(ch['hook'],q,'signal','ORIGINAL FICTION'),('THE TWIST',a,'signal','THE END')])
        return [scene(h,s,v,l,'ORIGINAL MICROFICTION',duration=2.1) for h,s,v,l in beats]
    kind=ch.get('kind','math')
    hook = 'Memorize these numbers.' if kind=='memory' else 'Try this before the answer appears.'
    narration = 'What was number '+re.search(r'#(\d)', ch['prompt']).group(1)+'?' if kind=='memory' else 'You have five seconds.'
    ans_speech = a.replace('·','and').replace('COL','column')
    return [scene(ch['hook'],hook,'quiz',ch['question'],'LOOK CLOSELY',duration=2.8,kind=kind),
            scene(ch['prompt'],narration,'quiz',ch['question'] if kind!='memory' else '?','LOCK IN YOUR ANSWER',duration=5.6,countdown=True,kind=kind),
            scene('THE ANSWER', 'The answer is '+ans_speech+'.','quiz',a,'DID YOU GET IT?',duration=2.6,answer=True)]


def ensure_voice_assets():
    root = Path(os.environ.get('ASTRA_VOICE_CACHE', str(Path.home()/'.cache/astra-voice')))
    root.mkdir(parents=True, exist_ok=True)
    for name, expected in MODEL_FILES.items():
        path = root/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==expected:
            continue
        tmp = path.with_suffix(path.suffix+'.part')
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client, client.stream('GET',ASSET_BASE+name) as r, tmp.open('wb') as f:
                r.raise_for_status()
                count=0
                for block in r.iter_bytes(1024*1024):
                    count+=len(block)
                    if count>400_000_000: raise ValueError('Voice asset too large')
                    f.write(block)
            if hashlib.sha256(tmp.read_bytes()).hexdigest()!=expected:
                raise RuntimeError('Voice asset checksum mismatch')
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    return root


@lru_cache(maxsize=1)
def voice_engine():
    # Restrict CPU threads so inference and encoding share a small cloud runner.
    os.environ.setdefault('OMP_NUM_THREADS','2')
    import onnxruntime as ort
    ort.disable_telemetry_events()
    from kokoro_onnx import Kokoro
    root=ensure_voice_assets()
    options=ort.SessionOptions()
    options.intra_op_num_threads=2
    options.inter_op_num_threads=1
    session=ort.InferenceSession(str(root/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    return Kokoro.from_session(session,str(root/'voices-v1.0.bin'))


def voice_plan(plan, genre):
    engine=voice_engine()
    cursor=0.0
    for s in plan:
        samples, rate=engine.create(s['speech'],voice='af_heart',speed=1.04 if genre!='fiction' else .98,lang='en-us')
        samples=np.asarray(samples,dtype=np.float32)
        if rate!=RATE or len(samples)==0 or not np.isfinite(samples).all():
            raise RuntimeError('Invalid narration audio; refusing to publish an incomplete video.')
        # Normalize each line gently, then mix with a substantially quieter score.
        peak=float(np.max(np.abs(samples)))
        if peak>0: samples=samples*(.65/peak)
        s.update(audio=samples,start=cursor,voice_start=cursor+.18,
                 duration=max(float(s['min_duration']),len(samples)/RATE+.55))
        s['end']=s['start']+s['duration']
        cursor=s['end']
    if not 6<=cursor<=58:
        raise RuntimeError(f'Video duration {cursor:.1f}s is outside the Studio short format.')
    return cursor


def score_audio(plan, duration, genre, path):
    """Procedural music, voice-aware ducking, stereo motion and soft transition hits."""
    n=int(math.ceil(duration*RATE)); t=np.arange(n,dtype=np.float32)/RATE
    rng=np.random.default_rng(2104)
    # Rounded synthesizer tones; different harmonic palette for each series.
    root={'space':146.832,'fiction':130.813,'tech':164.814,'football':146.832,'challenge':164.814}[genre]
    beat=60/(96 if genre in {'fiction','space'} else 112)
    phase=np.mod(t,beat)
    kick=np.sin(2*np.pi*(48*phase+20*(1-np.exp(-18*phase))/18))*np.exp(-phase*18)*.065
    melody=np.zeros(n,dtype=np.float32)
    for i in range(0,int(duration/(beat/2))+1):
        start=int(i*beat/2*RATE); length=min(int(beat*.48*RATE),n-start)
        if length<=0: continue
        u=np.arange(length,dtype=np.float32)/RATE
        note=root*2**([0,7,12,10,0,7,15,12][i%8]/12)
        melody[start:start+length]+=(np.sin(2*np.pi*note*u)+.23*np.sin(4*np.pi*note*u))*np.exp(-u*13)*.027
    pad=(np.sin(2*np.pi*root*.5*t)+np.sin(2*np.pi*root*.5*1.5*t))*.015
    music=kick+melody+pad
    duck=np.ones(n,dtype=np.float32)
    speech=np.zeros(n,dtype=np.float32); fx=np.zeros(n,dtype=np.float32)
    for s in plan:
        j=int(s['voice_start']*RATE); b=s['audio']; end=min(n,j+len(b))
        speech[j:end]+=b[:end-j]
        # Smooth 80 ms attack/release on music ducking; no pumping on every word.
        idx=np.arange(n,dtype=np.float32)/RATE
        env=np.minimum(np.clip((idx-s['voice_start']+.08)/.08,0,1),np.clip((s['voice_start']+len(b)/RATE+.12-idx)/.12,0,1))
        duck=np.minimum(duck,1-.70*env)
        k=int(s['start']*RATE); size=min(int(.24*RATE),n-k)
        u=np.arange(size,dtype=np.float32)/RATE
        noise=rng.normal(0,1,size).astype(np.float32)
        noise=np.convolve(noise,np.ones(12)/12,mode='same')
        fx[k:k+size]+=noise*np.sin(np.pi*np.arange(size)/max(1,size))*.048
        if s.get('answer'):
            fx[k:k+size]+=np.sin(2*np.pi*880*u)*np.exp(-u*14)*.08
        if s.get('countdown'):
            for second in range(1,6):
                pos=int((s['end']-second)*RATE); size=min(int(.055*RATE),n-pos)
                if pos>=0 and size>0:
                    u=np.arange(size)/RATE
                    fx[pos:pos+size]+=np.sin(2*np.pi*740*u)*np.exp(-u*80)*.042
    fade=np.minimum(np.clip(t/.10,0,1),np.clip((duration-t)/.18,0,1))
    backing=music*duck
    left=(speech+backing*(1+.09*np.sin(t*.8))+fx)*fade
    right=(speech+backing*(1-.09*np.sin(t*.8))+fx)*fade
    mixed=np.stack([left,right],axis=1)
    peak=float(np.max(np.abs(mixed)))
    if peak>.88: mixed*=.88/peak
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes((mixed*32767).astype('<i2').tobytes())
    return {'peak_dbfs':round(20*math.log10(max(float(np.max(np.abs(mixed))),1e-9)),2),'voice':'Kokoro af_heart','music':'original procedural score'}


@lru_cache(maxsize=5)
def background(genre):
    top,bottom,accent=THEMES[genre]
    y,x=np.mgrid[0:H,0:W]
    blend=y/H
    glow=np.exp(-(((x-W*.65)/(W*.8))**2+((y-H*.40)/(H*.48))**2)*3)
    arr=np.zeros((H,W,3),dtype=np.uint8)
    for c in range(3): arr[:,:,c]=np.clip(top[c]*(1-blend)+bottom[c]*blend+glow*accent[c]*.09,0,255)
    return Image.fromarray(arr)


@lru_cache(maxsize=4)
def planet_texture(earth=False, hot=False):
    n=600; y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]
    rr=x*x+y*y; mask=rr<=1; z=np.sqrt(np.maximum(0,1-rr))
    light=np.maximum(.10,-.50*x-.35*y+.78*z)
    clouds=.055*np.sin(x*29+y*11)+.035*np.cos(y*44+x*9)+.022*np.sin(x*73-y*39)
    if earth:
        land=(np.sin(x*11+y*7)+np.cos(y*13-x*8)+.5*np.sin(x*24+y*19))>.65
        base=np.stack([np.where(land,65,31),np.where(land,161,99),np.where(land,124,190)],axis=2)
    else:
        bands=np.sin(y*21+x*7+np.sin(y*6)*2)*.06+clouds
        base=np.stack([234+bands*100,142+bands*260,65+bands*170],axis=2)
        if hot: base[:,:,0]=255
    col=np.clip(base*light[:,:,None]+np.maximum(0,z-.92)[:,:,None]*100,0,255).astype(np.uint8)
    alpha=(mask*255).astype(np.uint8)
    return Image.fromarray(np.dstack([col,alpha]))


def starfield(d,t,accent):
    rng=np.random.default_rng(17)
    for x,y,r,phase in zip(rng.integers(45,1035,65),rng.integers(180,1550,65),rng.integers(1,4,65),rng.random(65)):
        v=int(70+90*(.5+.5*math.sin(t*.7+phase*6)))
        yy=int(y+math.sin(t*.23+phase)*9)
        d.ellipse((int(x-r),yy-int(r),int(x+r),yy+int(r)),fill=(v,v,min(255,v+25)))


def draw_visual(im,s,t,u,accent):
    d=ImageDraw.Draw(im); visual=s['visual']; p=ease(u/.55)
    # All graphics live above the caption zone, away from Shorts controls.
    cx,cy=505,865
    if visual in {'planet','orbit','compare'}:
        starfield(d,t,accent)
        if visual=='planet':
            size=int(490+28*math.sin(t*.18)+20*p)
            texture=planet_texture(s.get('label')=='EARTH',s.get('hot',False)).resize((size,size),Image.Resampling.LANCZOS)
            halo=Image.new('RGBA',im.size,(0,0,0,0)); hd=ImageDraw.Draw(halo)
            hd.ellipse((cx-size/2-8,cy-size/2-8,cx+size/2+8,cy+size/2+8),fill=accent+(70,))
            im.paste(Image.alpha_composite(im.convert('RGBA'),halo.filter(ImageFilter.GaussianBlur(24))).convert('RGB'))
            im.paste(texture,(int(cx-size/2),int(cy-size/2)),texture)
            d=ImageDraw.Draw(im)
            for k in range(3):
                angle=int(t*28+k*110)
                d.arc((cx-size*.67,cy-size*.30,cx+size*.67,cy+size*.30),angle,angle+70,fill=accent,width=3)
        elif visual=='orbit':
            d.ellipse((160,650,850,1080),outline=(67,77,107),width=3)
            d.ellipse((460,818,550,908),fill=(255,210,131))
            angle=t*.7
            px,py=cx+345*math.cos(angle),865+215*math.sin(angle)
            tex=planet_texture().resize((150,150),Image.Resampling.LANCZOS)
            im.paste(tex,(int(px-75),int(py-75)),tex)
        else:
            for yy,value,total,color,title in [(780,243,243,accent,'ONE ROTATION'),(955,225,243,(129,185,255),'ONE ORBIT')]:
                d.text((130,yy-54),title,font=font(27),fill=(181,190,213))
                d.rounded_rectangle((130,yy,900,yy+48),radius=24,fill=(28,33,55))
                d.rounded_rectangle((130,yy,130+770*value/total*p,yy+48),radius=24,fill=color)
        d=ImageDraw.Draw(im)
        fit_text(d,s['label'],(80,1090,935,1240),size=104,fill=accent,max_lines=2)
        fit_text(d,s['sub'],(85,1245,930,1310),size=27,fill=(184,192,214),max_lines=2)
    elif visual=='pitch':
        for i in range(7):
            d.polygon([(115+i*118,650),(233+i*118,650),(258+i*108,1090),(145+i*108,1090)],fill=(9,53+(i%2)*8,48))
        d.rectangle((115,650,925,1090),outline=(91,150,131),width=3)
        d.line((520,650,520,1090),fill=(91,150,131),width=3)
        d.ellipse((435,790,605,950),outline=(91,150,131),width=3)
        d.rectangle((770,746,925,995),outline=(91,150,131),width=3)
        if s.get('rule')=='added-time':
            d.rounded_rectangle((230,748,805,970),radius=28,fill=(8,17,23),outline=accent,width=3)
            fit_text(d,'+5',(250,760,785,950),size=170,fill=accent)
        else:
            d.line((715,660,715,1080),fill=(249,146,111),width=4)
            for x,y,col in [(310,830,accent),(750,790,accent),(690,950,(114,157,239)),(815,930,(114,157,239)),(580,730,(114,157,239))]:
                yy=y+int(math.sin(t*1.6+x)*5)
                d.ellipse((x-26,yy-26,x+26,yy+26),fill=col,outline=(235,248,243),width=3)
            progress=(u*.35)%1
            bx,by=330+405*progress,830-32*progress
            d.line((330,830,730,798),fill=(100,152,137),width=3)
            d.ellipse((bx-13,by-13,bx+13,by+13),fill='white')
        fit_text(d,s['label'],(80,1120,940,1220),size=65,fill=accent)
        fit_text(d,s['sub'],(80,1235,940,1300),size=27,fill=(166,196,186))
    elif visual in {'screen','keys'}:
        d.rounded_rectangle((90,640,945,1090),radius=36,fill=(19,31,52),outline=(60,97,132),width=3)
        d.line((92,706,943,706),fill=(60,97,132),width=2)
        for i,col in enumerate([(250,115,125),(249,192,91),(85,215,168)]):
            d.ellipse((120+i*34,661,135+i*34,676),fill=col)
        if visual=='keys':
            keys=s.get('keys',['WIN']); count=len(keys); kw=210 if count==3 else 275
            total=count*kw+(count-1)*24; left=(1035-total)/2
            for i,key in enumerate(keys):
                x=left+i*(kw+24); bump=int(8*math.sin(max(0,u-i*.12)*4)) if u<1.4 else 0
                d.rounded_rectangle((x,787+bump,x+kw,973+bump),radius=22,fill=(35,60,86),outline=accent,width=3)
                fit_text(d,key,(x+12,790+bump,x+kw-12,960+bump),size=49,fill=accent)
        else:
            for k,width in enumerate([570,410,510]):
                y=760+k*92
                d.rounded_rectangle((145,y,145+width, y+54),radius=12,fill=(40,67,95))
                if s.get('tool')=='taskmanager':
                    d.rounded_rectangle((160,y+13,160+int((width-30)*(.4+.25*math.sin(t+k))),y+41),radius=6,fill=accent)
            if s.get('tool')=='screenshot': d.rectangle((250,778,766,991),outline=accent,width=4)
            cursor=(int(645+math.sin(t)*90),int(935+math.cos(t*.8)*30))
            d.polygon([cursor,(cursor[0]+5,cursor[1]+48),(cursor[0]+17,cursor[1]+30),(cursor[0]+35,cursor[1]+31)],fill='white')
        fit_text(d,s['label'],(80,1135,940,1230),size=65,fill=accent)
        fit_text(d,s['sub'],(80,1240,940,1300),size=27,fill=(176,204,224))
    elif visual in {'ship','signal','door','robot','forest'}:
        starfield(d,t,accent)
        if visual=='ship':
            dy=int(math.sin(t*.7)*15)
            d.ellipse((370,785+dy,710,965+dy),outline=(89,91,131),width=3)
            d.polygon([(185,890+dy),(500,720+dy),(845,890+dy),(500,850+dy)],fill=(123,131,163))
            d.polygon([(385,870+dy),(500,742+dy),(622,870+dy)],fill=(214,221,244))
            d.ellipse((452,858+dy,552,881+dy),fill=accent)
        elif visual=='signal':
            for k in range(4):
                radius=65+((t*55+k*64)%290)
                d.ellipse((cx-radius,cy-radius*.55,cx+radius,cy+radius*.55),outline=(65+k*16,62+k*14,98+k*20),width=3)
            points=[(int(x),int(870+math.sin(x*.06+t*8)*math.sin(x*.014-t)*75)) for x in range(170,850,4)]
            d.line(points,fill=accent,width=4)
        elif visual=='door':
            d.polygon([(270,1130),(380,640),(680,640),(820,1130)],fill=(22,27,45))
            d.rectangle((368,621,690,1108),fill=(5,8,22),outline=accent,width=5)
            gap=30+int(85*ease(u/2))
            d.polygon([(385,641),(665-gap,684),(665-gap,1055),(385,1090)],fill=(54,51,83),outline=(137,128,183))
            d.ellipse((615-gap,858,629-gap,873),fill=accent)
            d.polygon([(665-gap,684),(676,639),(676,1095),(665-gap,1055)],fill=(209,197,251))
        elif visual=='robot':
            d.rounded_rectangle((355,720,675,984),radius=45,fill=(90,110,123),outline=(194,212,214),width=4)
            d.rounded_rectangle((389,772,640,875),radius=22,fill=(12,26,38))
            for x in [447,576]:d.ellipse((x-19,801,x+19,837),fill=accent)
            d.line((512,720,512,666),fill=(151,171,187),width=7)
            d.ellipse((501,647,523,669),fill=accent)
            d.ellipse((483,1020,553,1060),fill=(93,171,128))
        else:
            for i in range(8):
                x=130+i*105; y=710+70*math.sin(i*3); sway=int(math.sin(t+i)*5)
                d.rectangle((x-8, y+150,x+8,1120),fill=(63,84,79))
                d.polygon([(x+sway,y),(x-90,y+290),(x+90,y+290)],fill=(36,105+(i%3)*13,84))
        fit_text(d,s['label'],(80,1145,940,1250),size=61,fill=accent)
    else:
        # Animated circular dial and large central challenge. No stock puzzle footage.
        d.ellipse((155,575,855,1195),outline=(64,52,94),width=4)
        d.arc((142,562,868,1208),-90,-90+max(1,int(360*(1-min(1,u/s['duration'])))),fill=accent,width=9)
        fit_text(d,s['label'],(185,695,825,1100),size=94,fill=accent if s.get('answer') else 'white',max_lines=5)
        if s.get('countdown'):
            remain=max(1,math.ceil(s['duration']-u))
            d.rounded_rectangle((444,1200,570,1300),radius=25,fill=accent)
            fit_text(d,str(min(5,remain)),(450,1200,564,1300),size=65,fill=(17,15,28))


def render_frame(plan,t,genre,total):
    index=next((i for i,s in enumerate(plan) if t<s['end']),len(plan)-1)
    s=plan[index];u=t-s['start']; accent=THEMES[genre][2]
    im=background(genre).copy()
    draw_visual(im,s,t,u,accent)
    d=ImageDraw.Draw(im)
    # Consistent top bar and compact scene index.
    d.rounded_rectangle((70,130,126,186),radius=16,fill=accent)
    d.text((98,158),'L',font=font(37),anchor='mm',fill=(12,17,28))
    d.text((148,143),'LOKI',font=font(33),fill=(237,240,250))
    d.text((148,182),('ORIGINAL FICTION' if genre=='fiction' else genre.upper()+' / SHORT CUTS'),font=font(20),fill=(141,159,183))
    d.text((935,162),f'{index+1:02d} / {len(plan):02d}',font=font(25),anchor='rm',fill=accent)
    headline_offset=int((1-ease(u/.30))*24)
    fit_text(d,s['headline'],(70,266+headline_offset,940,515+headline_offset),size=84,fill='white',max_lines=3)
    # Phrase captions use actual utterance windows; active word timing is approximate.
    words=s['speech'].split()
    dur=len(s['audio'])/RATE
    pos=max(0,min(len(words)-1,int((t-s['voice_start'])/max(.1,dur)*len(words))))
    chunk=pos//5; text=' '.join(words[chunk*5:(chunk+1)*5])
    if s.get('countdown') and t>s['voice_start']+dur+.1: text='YOUR TURN'
    d.rounded_rectangle((75,1370,950,1570),radius=28,fill=(8,12,23))
    fit_text(d,text,(104,1384,921,1555),size=59,fill=accent,max_lines=2)
    d.line((75,1620,950,1620),fill=(53,59,80),width=4)
    d.line((75,1620,75+875*min(1,t/total),1620),fill=accent,width=4)
    d.text((75,1660),'LOKI THE GAME CHANGER',font=font(22),fill=(144,158,180))
    # Brief ink-dark cut transition rather than full-screen flashing.
    if index>0 and u<.13:
        shade=Image.new('RGB',im.size,(8,12,23)); im=Image.blend(shade,im,.55+.45*u/.13)
    return im


def render_short(ch,out,still_dir=None):
    genre=ch.get('genre','challenge')
    if genre not in THEMES: raise ValueError('Unsupported genre')
    plan=make_plan(ch);duration=voice_plan(plan,genre)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='astra_studio_') as tmp:
        tmp=Path(tmp);audio=tmp/'mix.wav'
        audio_info=score_audio(plan,duration,genre,audio)
        count=math.ceil(duration*FPS);actual_duration=count/FPS
        cmd=[get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0',
             '-i',str(audio),'-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','18',
             '-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
             '-af','loudnorm=I=-16:TP=-1.5:LRA=9','-movflags','+faststart','-shortest',str(out)]
        with (tmp/'ffmpeg.log').open('wb') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(count):
                    proc.stdin.write(render_frame(plan,i/FPS,genre,duration).tobytes())
                proc.stdin.close()
                if proc.wait(timeout=120)!=0: raise RuntimeError('FFmpeg could not encode Studio output.')
            except Exception:
                proc.kill();proc.wait();raise
        if still_dir:
            folder=Path(still_dir);folder.mkdir(parents=True,exist_ok=True)
            for i,s in enumerate(plan): render_frame(plan,s['start']+min(1,s['duration']/2),genre,duration).save(folder/f'scene_{i+1}.jpg',quality=94)
    report={'renderer':VERSION,'genre':genre,'frames':count,'duration':round(actual_duration,3),
            'resolution':[W,H],'fps':FPS,'audio':audio_info,
            'scenes':[{k:v for k,v in s.items() if k!='audio'} for s in plan]}
    print('Studio render:',json.dumps({k:v for k,v in report.items() if k!='scenes'}))
    return report


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Render a Studio preview without authentication or uploads.')
    parser.add_argument('--preview',required=True,type=Path)
    args=parser.parse_args()
    demo=dict(genre='space',content_id='venus-spin',hook='ONE SPIN',
              question='Venus rotates slowly.',answer='243 Earth days per rotation.')
    render_short(demo,args.preview)
