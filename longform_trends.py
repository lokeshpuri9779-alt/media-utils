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


SENSITIVE_TREND_RE = re.compile(
    r'\b(election|vote|president|prime minister|minister|government|war|missile|attack|shooting|'
    r'killed|dead|death|earthquake|flood|cyclone|hurricane|outbreak|vaccine|disease|health|hospital|'
    r'stock|crypto|bitcoin|market crash|bank|inflation|interest rate|lawsuit|court|arrest)\b', re.I
)

def _host(url):
    from urllib.parse import urlparse
    try:
        parsed=urlparse(str(url or '').strip())
    except ValueError:
        return ''
    if parsed.scheme not in {'http','https'} or not parsed.hostname:
        return ''
    host=parsed.hostname.lower()
    return host[4:] if host.startswith('www.') else host

def _distinct_news(items):
    out=[]; seen=set()
    for x in items or []:
        if not isinstance(x,dict) or not x.get('title') or not x.get('url') or not x.get('source'):
            continue
        host=_host(x.get('url'))
        if not host or host in seen:
            continue
        seen.add(host); out.append(x)
    return out

def _sensitive(topic, news):
    text=' '.join([str(topic or '')]+[str(x.get('title') or '') for x in news or []])
    return bool(SENSITIVE_TREND_RE.search(text))

def sourced_topics(items, limit=5):
    ranked=[]; seen=set()
    for item in items or []:
        topic=' '.join(str(item.get('title') or '').split()).strip()
        news=_distinct_news(item.get('news') or [])
        key=re.sub(r'[^a-z0-9]+',' ',topic.lower()).strip()
        if not topic or not news or not key or key in seen:
            continue
        sensitive=_sensitive(topic,news)
        if sensitive and len(news) < 2:
            continue
        seen.add(key)
        first=news[0]
        # Keep two independent sources when available so non-sensitive
        # topics can qualify for evidence-backed deep dives too.
        chosen=news[:2]
        ranked.append({
            'topic':topic[:120],
            'region':str(item.get('region') or 'global')[:24],
            'traffic':str(item.get('traffic') or '')[:40],
            'headline':' '.join(str(first['title']).split())[:220],
            'source':' '.join(str(first['source']).split())[:100],
            'url':str(first['url'])[:1000],
            'source_names':' / '.join(' '.join(str(x['source']).split())[:100] for x in chosen),
            'sources':[{'source':' '.join(str(x['source']).split())[:100],
                        'url':str(x['url'])[:1000]} for x in chosen],
            'sensitive':sensitive,
            'score':_traffic_number(item.get('traffic')),
        })
    ranked.sort(key=lambda x:(x['score'],x['topic']),reverse=True)
    return ranked[:limit]

def story_candidate(items):
    """Pick one source-deep topic for a coherent long-form story."""
    topics=sourced_topics(items,limit=8)
    deep=[]
    for t in topics:
        # Long-form needs independent reporting even when the topic is not
        # sensitive; one headline is not enough substance for a deep story.
        if len(t.get('sources') or []) >= 2:
            deep.append(t)
    return deep[0] if deep else None

def available(items, minimum=1):
    return story_candidate(items) is not None

def build_plan(items):
    t=story_candidate(items)
    if not t:
        raise RuntimeError('No trend has enough independent source depth for a quality long-form story.')
    topic=t['topic']; headline=t['headline']; sources=t['source_names']
    # One subject, multiple narrative functions. Repetition is deliberate only
    # where it reinforces the central promise; scenes otherwise advance it.
    beats=[
      ('THE STORY BEHIND THE SURGE',
       f'{topic} is drawing fresh search interest. The useful question is what actually changed, and why people are paying attention now.',
       'signal',topic[:54].upper(),'THE PROMISE'),
      ('WHAT CHANGED?',
       f'Current source-linked reporting centers on this development: {headline}',
       'screen','THE CATALYST','WHAT WE KNOW'),
      ('WHY NOW?',
       f'The attention spike matters only if it connects to a real development. Reporting from {sources} gives us independent context rather than treating search volume as proof.',
       'signal','ATTENTION + EVENT','THE CONTEXT'),
      ('THE EVIDENCE',
       f'Two independent source domains are attached to this story. The primary reported angle is: {headline}',
       'screen','SOURCE CHECK','VERIFY, DON’T GUESS'),
      ('WHAT PEOPLE MAY MISS',
       f'The headline and the search spike are not the same thing. For {topic}, separate what the sources actually report from assumptions created by the trend itself.',
       'signal','SIGNAL ≠ CONCLUSION','THE COMPLICATION'),
      ('WHY IT MATTERS',
       f'This story is worth following because a measurable attention shift is now attached to source-linked reporting. The consequence is not popularity itself; it is what the underlying event may change next.',
       'screen','CONSEQUENCE > HYPE','THE IMPLICATION'),
      ('WHAT TO WATCH NEXT',
       f'Watch for new verified reporting around {topic}. If later facts change the picture, the sources should lead the update—not the trend chart.',
       'signal','NEXT DEVELOPMENT','THE OUTLOOK'),
      ('THE TAKEAWAY',
       f'{topic} earned attention, but attention was only the starting signal. RAYVAN follows the evidence, builds the context, and leaves uncertainty visible.',
       'screen','STORIES BEYOND THE ORDINARY','RAYVAN'),
    ]
    beat_names=['promise','catalyst','context','evidence','complication','implication','outlook','takeaway']
    visual_modes=['signal','evidence','map','evidence','contrast','impact','timeline','payoff']
    plan=[]
    for i,(h,speech,visual,label,sub) in enumerate(beats,1):
        # Long-form uses explicit narrative beats so visuals, pacing and later
        # retention learning can reason about structure instead of scene number.
        plan.append(studio.scene(h,speech,visual_modes[i-1],label,sub,duration=12.0,
                                 section=i,source=t['source'],topic=topic,
                                 story_beat=beat_names[i-1]))
    return plan,[t]

def long_quality_gate(plan,topics):
    if not plan or not topics: raise RuntimeError('Long-form creative gate: empty story.')
    beats=[x.get('story_beat') for x in plan]
    sources=topics[0].get('sources') or []
    score=45
    score+=min(20,len(set(beats))*3)
    score+=15 if len(sources)>=2 else -30
    score+=10 if {'promise','evidence','complication','implication','takeaway'}.issubset(set(beats)) else -20
    score+=10 if len(set(x.get('visual') for x in plan))>=5 else -15
    report={'score':score,'beats':beats,'visual_modes':[x.get('visual') for x in plan],
            'source_count':len(sources)}
    if score<75: raise RuntimeError('Long-form creative gate rejected weak story: '+json.dumps(report))
    return report


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
    d.text((140,62),'RAYVAN / EXPLAINED',font=studio.font(27),fill=(224,235,247))
    d.text((1845,67),f'{index+1:02d} / {len(plan):02d}',font=studio.font(24),fill=accent,anchor='rm')

    section=int(s.get('section') or 0)
    if section:
        d.text((86,210),f'CHAPTER {section:02d}',font=studio.font(28),fill=accent)
    studio.fit_text(d,s['headline'],(80,250,1180,535),size=92,fill='white',align='left',max_lines=3)

    d.rounded_rectangle((1240,210,1845,690),radius=34,fill=(13,27,45),outline=(48,91,124),width=3)
    studio.fit_text(d,s.get('label',''),(1280,260,1805,475),size=64,fill=accent,max_lines=4)
    studio.fit_text(d,s.get('sub',''),(1280,520,1805,640),size=28,fill=(178,202,221),max_lines=3)

    if s['visual'] in {'signal','timeline'}:
        points=[]
        for xx in range(100,1110,10):
            yy=720+math.sin(xx*.018+t*4)*38+math.sin(xx*.006-t*1.3)*56
            points.append((xx,int(yy)))
        d.line(points,fill=accent,width=5)
        for k in range(3):
            r=60+((t*50+k*90)%280)
            d.ellipse((605-r,725-r*.45,605+r,725+r*.45),outline=(39+20*k,77+20*k,105+25*k),width=2)
    elif s['visual'] in {'evidence','contrast'}:
        d.rounded_rectangle((110,650,1120,845),radius=26,fill=(18,36,58),outline=(48,91,124),width=3)
        widths=(650,850) if s['visual']=='contrast' else (675,865)
        for j,w in enumerate(widths):
            d.rounded_rectangle((145,700+j*72,145+w,742+j*72),radius=12,fill=(41+j*15,80+j*8,112+j*12))
        d.text((160,665),'SOURCE CHECK' if s['visual']=='evidence' else 'COMPARE THE CLAIMS',font=studio.font(25),fill=accent)
    elif s['visual']=='map':
        d.ellipse((250,600,940,900),outline=accent,width=6)
        for k in range(7):
            ang=k*.9+t*.15; x=595+math.cos(ang)*250; y=750+math.sin(ang)*110
            d.ellipse((x-12,y-12,x+12,y+12),fill=accent)
        d.line((595,750,845,680),fill=(178,202,221),width=4)
    elif s['visual']=='impact':
        for k,val in enumerate((.32,.58,.82)):
            x=180+k*300; h=int(260*val*(.75+.25*math.sin(t*1.4+k)))
            d.rounded_rectangle((x,860-h,x+170,860),radius=18,fill=(45+25*k,100+15*k,145+20*k))
    else:
        # Payoff scene deliberately simplifies composition after denser evidence.
        d.ellipse((360,620,870,900),fill=(20,52,78),outline=accent,width=5)
        d.text((615,760),'WHY IT MATTERS',font=studio.font(48),fill='white',anchor='mm')

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
    top=topics[0]['topic'].upper() if topics else 'CURRENT STORY'
    # Thumbnail promise is topic-first; avoid the same generic WHAT CHANGED card.
    promise=('WHY NOW?' if len(top)<34 else 'THE STORY\nBEHIND IT')
    studio.fit_text(d,promise,(90,220,1080,850),size=170,fill=(114,209,255),align='left',max_lines=2)
    studio.fit_text(d,top,(1120,260,1820,790),size=68,fill='white',max_lines=5)
    d.text((95,965),'ONE STORY / MULTIPLE SOURCES / CONTEXT > HYPE',font=studio.font(30),fill=(175,199,219))
    im.resize((1280,720),Image.Resampling.LANCZOS).save(path,'JPEG',quality=92)


def render(out, episode_id, trend_items):
    plan,topics=build_plan(trend_items)
    # Apply only evidence-backed pacing lessons; absent evidence leaves the
    # authored structure untouched.
    try:
        import json as _json
        perf_path=Path(__file__).with_name('performance.json')
        perf=_json.loads(perf_path.read_text(encoding='utf-8')) if perf_path.exists() else {}
        lessons=(((perf.get('evolution') or {}).get('long_retention_patterns') or {}).get('lessons') or [])
    except Exception:
        lessons=[]
    if 'stronger_open' in lessons and plan:
        plan[0]['min_duration']=max(8.0,float(plan[0].get('min_duration') or 12.0)-2.0)
    if 'shorter_context' in lessons:
        for x in plan:
            if x.get('story_beat') in {'context','complication'}: x['min_duration']=9.0
    if 'earlier_implication' in lessons:
        ii=next((i for i,x in enumerate(plan) if x.get('story_beat')=='implication'),None)
        if ii is not None and ii>4:
            item=plan.pop(ii); plan.insert(4,item)
    quality=long_quality_gate(plan,topics)
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
    source_rows=[]; seen_urls=set()
    for x in topics:
        for s in x.get('sources',[]):
            if s['url'] in seen_urls:
                continue
            seen_urls.add(s['url'])
            source_rows.append(f"- {s['source']}: {s['url']}")
    sources='\n'.join(source_rows)
    description=(
        'A source-linked RAYVAN explainer built around one live story with independent reporting. '
        'Trend status is treated as a signal, not proof of importance.\n\nSources:\n'+sources+
        '\n\nRAYVAN — Stories Beyond the Ordinary.\n'
        'Original motion graphics and music; AI-assisted production and synthetic narration.'
    )
    report={
        'renderer':studio.VERSION,'format':'long','genre':'current','content_id':episode_id,
        'duration':round(total,3),'resolution':[1920,1080],'fps':studio.FPS,
        'scene_count':len(plan),'topic_count':1,'story_mode':'single-topic-deep-dive','audio':audio_info,
        'thumbnail':str(thumb),'sources':[s['url'] for x in topics for s in x.get('sources',[])],
        'creative_quality':quality,'story_beats':[x.get('story_beat') for x in plan],
        'scenes':[{k:v for k,v in x.items() if k!='audio'} for x in plan],
    }
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Trend long-form complete:',json.dumps(report),flush=True)
    topic=topics[0]['topic'] if topics else 'Current Story'
    # Natural, topic-led packaging; distribution.py may refine this later from
    # measured search/browse evidence without adding unsupported claims.
    return f'Why {topic} Is Getting Attention Now | RAYVAN',description,report
