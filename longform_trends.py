"""Source-linked long-form trend brief for RAYVAN.

This renderer uses only live search-interest metadata and linked news headlines.
It does not copy article bodies or invent factual details beyond the supplied
source context. If enough sourced topics are unavailable it refuses to render.
"""
from __future__ import annotations

import json, math, re, subprocess, tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import studio_renderer as studio


def _traffic_number(value: str) -> int:
    text=str(value or '').upper().replace(',','').replace('+','').strip()
    m=re.match(r'([0-9.]+)\s*([KMB]?)',text)
    if not m:
        return 0
    n=float(m.group(1)); mult={'':1,'K':1_000,'M':1_000_000,'B':1_000_000_000}[m.group(2)]
    return int(n*mult)


def sourced_topics(items, limit=5):
    ranked=[]; seen=set()
    for item in items or []:
        topic=' '.join(str(item.get('title') or '').split()).strip()
        news=[x for x in (item.get('news') or []) if x.get('title') and x.get('url') and x.get('source')]
        key=re.sub(r'[^a-z0-9]+',' ',topic.lower()).strip()
        if not topic or not news or not key or key in seen:
            continue
        seen.add(key)
        first=news[0]
        ranked.append({
            'topic':topic[:120],
            'region':str(item.get('region') or 'global')[:24],
            'traffic':str(item.get('traffic') or '')[:40],
            'headline':' '.join(str(first['title']).split())[:220],
            'source':' '.join(str(first['source']).split())[:100],
            'url':str(first['url'])[:1000],
            'score':_traffic_number(item.get('traffic')),
        })
    ranked.sort(key=lambda x:(x['score'],x['topic']),reverse=True)
    return ranked[:limit]


def available(items, minimum=4):
    return len(sourced_topics(items,limit=5)) >= minimum


def build_plan(items):
    topics=sourced_topics(items,limit=5)
    if len(topics) < 4:
        raise RuntimeError('Not enough source-linked live trends for a quality long-form brief.')
    plan=[
        studio.scene(
            'WHAT IS SURGING RIGHT NOW?',
            'Instead of chasing random viral clips, this RAYVAN brief starts with live search-interest signals and source-linked reporting.',
            'signal','LIVE SEARCH','SOURCE-LINKED TREND BRIEF',duration=4.5
        )
    ]
    for i,t in enumerate(topics,1):
        traffic=(f" / {t['traffic']}" if t['traffic'] else '')
        plan.extend([
            studio.scene(
                f'{i:02d} / {t["topic"]}',
                f"{t['topic']} is drawing a fresh wave of search interest in {t['region']}. Search interest tells us where attention is moving; it does not prove why.",
                'signal',t['topic'][:54].upper(),f"{t['region'].upper()}{traffic}",duration=4.0,section=i,source=t['source']
            ),
            studio.scene(
                'THE CURRENT CATALYST',
                f"One current catalyst is coverage from {t['source']}. Its headline focuses on this angle: {t['headline']}",
                'screen',t['source'].upper()[:38],'CURRENT REPORTING',duration=4.0,section=i,source=t['source']
            ),
            studio.scene(
                'WHY THIS DESERVES ATTENTION',
                'The useful question is not whether a topic is viral. It is whether the underlying event changes what people should understand, watch, or verify next.',
                'signal','CONTEXT > HYPE','RAYVAN FILTER',duration=4.0,section=i,source=t['source']
            ),
            studio.scene(
                'WHAT TO WATCH NEXT',
                f"Watch the underlying story around {t['topic']} and verify new details at the linked source. RAYVAN treats the trend as a signal, not a conclusion.",
                'screen','FOLLOW THE SOURCE',t['source'].upper()[:38],duration=4.0,section=i,source=t['source']
            ),
        ])
    plan.append(studio.scene(
        'THE SIGNAL IS ONLY THE START',
        'Trends show where attention is moving. Good storytelling adds context, verification, and perspective. That is the standard RAYVAN will keep using.',
        'signal','STORIES BEYOND THE ORDINARY','RAYVAN',duration=4.5,section=6,source='RAYVAN'
    ))
    return plan,topics


def _background():
    y,x=np.mgrid[0:1080,0:1920]
    glow=np.exp(-(((x-1280)/1050)**2+((y-400)/720)**2)*2.3)
    arr=np.zeros((1080,1920,3),dtype=np.uint8)
    arr[:,:,0]=np.clip(7+glow*18,0,255)
    arr[:,:,1]=np.clip(13+glow*35,0,255)
    arr[:,:,2]=np.clip(26+glow*55,0,255)
    return Image.fromarray(arr)


def frame(plan,t,total):
    index=next((i for i,s in enumerate(plan) if t<s['end']),len(plan)-1)
    s=plan[index]; u=t-s['start']; accent=(114,209,255)
    im=_background(); d=ImageDraw.Draw(im)

    d.rounded_rectangle((62,48,116,102),radius=15,fill=accent)
    d.text((89,75),'R',font=studio.font(34),fill=(7,13,24),anchor='mm')
    d.text((140,62),'RAYVAN / TREND BRIEF',font=studio.font(27),fill=(224,235,247))
    d.text((1845,67),f'{index+1:02d} / {len(plan):02d}',font=studio.font(24),fill=accent,anchor='rm')

    section=int(s.get('section') or 0)
    if section:
        d.text((86,210),f'STORY {section:02d}',font=studio.font(28),fill=accent)
    studio.fit_text(d,s['headline'],(80,250,1180,535),size=92,fill='white',align='left',max_lines=3)

    d.rounded_rectangle((1240,210,1845,690),radius=34,fill=(13,27,45),outline=(48,91,124),width=3)
    studio.fit_text(d,s.get('label',''),(1280,260,1805,475),size=64,fill=accent,max_lines=4)
    studio.fit_text(d,s.get('sub',''),(1280,520,1805,640),size=28,fill=(178,202,221),max_lines=3)

    if s['visual']=='signal':
        points=[]
        for xx in range(100,1110,10):
            yy=720+math.sin(xx*.018+t*4)*38+math.sin(xx*.006-t*1.3)*56
            points.append((xx,int(yy)))
        d.line(points,fill=accent,width=5)
        for k in range(3):
            r=60+((t*50+k*90)%280)
            d.ellipse((605-r,725-r*.45,605+r,725+r*.45),outline=(39+20*k,77+20*k,105+25*k),width=2)
    else:
        d.rounded_rectangle((110,670,1120,835),radius=26,fill=(18,36,58),outline=(48,91,124),width=3)
        d.rounded_rectangle((145,705,820,745),radius=12,fill=(41,80,112))
        d.rounded_rectangle((145,768,1010,808),radius=12,fill=(31,61,88))

    words=s['speech'].split()
    dur=max(.1,len(s['audio'])/studio.RATE)
    pos=max(0,min(len(words)-1,int((t-s['voice_start'])/dur*len(words))))
    chunk=max(0,pos//10)
    caption=' '.join(words[chunk*10:(chunk+1)*10])
    d.rounded_rectangle((80,880,1845,1018),radius=28,fill=(6,12,22))
    studio.fit_text(d,caption,(115,895,1810,1003),size=42,fill=(222,235,246),max_lines=2)
    d.line((80,1045,1845,1045),fill=(42,65,84),width=4)
    d.line((80,1045,80+1765*min(1,t/total),1045),fill=accent,width=4)

    if index and u<.14:
        shade=Image.new('RGB',im.size,(7,13,24))
        im=Image.blend(shade,im,.52+.48*u/.14)
    return im


def thumbnail(path, topics):
    im=_background(); d=ImageDraw.Draw(im)
    d.text((90,90),'RAYVAN',font=studio.font(44),fill=(224,235,247))
    studio.fit_text(d,'WHAT IS\nSURGING\nRIGHT NOW?',(90,220,1080,850),size=150,fill=(114,209,255),align='left',max_lines=3)
    top=topics[0]['topic'].upper() if topics else 'LIVE TREND BRIEF'
    studio.fit_text(d,top,(1180,300,1820,760),size=72,fill='white',max_lines=4)
    d.text((95,965),'SOURCE-LINKED / CONTEXT > HYPE',font=studio.font(30),fill=(175,199,219))
    im.resize((1280,720),Image.Resampling.LANCZOS).save(path,'JPEG',quality=92)


def render(out, episode_id, trend_items):
    plan,topics=build_plan(trend_items)
    total=studio.voice_plan(plan,'current',max_duration=600)
    if total < 90:
        raise RuntimeError('Trend brief is too short to qualify as long-form.')
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='astra_trend_long_') as td:
        td=Path(td); audio=td/'mix.wav'
        audio_info=studio.score_audio(plan,total,'current',audio)
        count=math.ceil(total*studio.FPS)
        cmd=[studio.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(studio.FPS),'-i','pipe:0',
             '-i',str(audio),'-c:v','libx264','-preset','fast','-crf','18','-threads','2',
             '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
             '-af','loudnorm=I=-16:TP=-1.5:LRA=9','-shortest','-movflags','+faststart',str(out)]
        with (td/'ffmpeg.log').open('wb') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(count):
                    proc.stdin.write(frame(plan,i/studio.FPS,total).tobytes())
                    if i and i%(studio.FPS*30)==0:
                        print('Trend long-form rendered seconds:',i//studio.FPS,flush=True)
                proc.stdin.close()
                if proc.wait(timeout=120):
                    raise RuntimeError('Trend long-form encoding failed')
            except Exception:
                proc.kill(); proc.wait(); raise

    thumb=out.with_suffix('.jpg'); thumbnail(thumb,topics)
    sources='\n'.join(f"- {x['source']}: {x['url']}" for x in topics)
    description=(
        'A source-linked RAYVAN brief built from live search-interest signals. '
        'Trend status is treated as a signal, not proof of importance.\n\nSources:\n'+sources+
        '\n\nRAYVAN — Stories Beyond the Ordinary.\n'
        'Original motion graphics and music; AI-assisted production and synthetic narration.'
    )
    report={
        'renderer':studio.VERSION,'format':'long','genre':'current','content_id':episode_id,
        'duration':round(total,3),'resolution':[1920,1080],'fps':studio.FPS,
        'scene_count':len(plan),'topic_count':len(topics),'audio':audio_info,
        'thumbnail':str(thumb),'sources':[x['url'] for x in topics],
    }
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Trend long-form complete:',json.dumps(report),flush=True)
    return '5 Stories Surging Right Now | RAYVAN Trend Brief',description,report
