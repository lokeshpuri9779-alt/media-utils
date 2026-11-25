"""Source-linked long-form trend brief for RAYVAN.

This renderer uses only live search-interest metadata and linked news headlines.
It does not copy article bodies or invent factual details beyond the supplied
source context. If enough sourced topics are unavailable it refuses to render.
"""
from __future__ import annotations

import json, math, re, subprocess, tempfile, wave
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

# Do not count regional domains of the same news publisher as independent
# reporting (e.g. espn.com and espn.ph). This is intentionally conservative.
_TOPIC_NOISE = frozenset(
    'why what how is are the a an in on at of for to with and or vs versus '
    'today latest live score scores news update updates 2025 2026 now '
    'getting attention trending highlights result results breaking'.split()
)


def _topic_relevant(topic, headline):
    """Require a headline to mention a meaningful token of the trend topic.

    Trend-provider news lists can contain unrelated headlines. A link's URL or
    the source's brand alone cannot establish topical relevance.
    """
    anchors = {word for word in re.findall(r'[a-z0-9]+', str(topic or '').lower())
               if len(word) >= 3 and word not in _TOPIC_NOISE}
    words = set(re.findall(r'[a-z0-9]+', str(headline or '').lower()))
    return bool(anchors and anchors & words)


def _publisher_key(host):
    parts = host.split('.')
    if len(parts) < 2:
        return host
    if (len(parts) >= 3 and len(parts[-1]) == 2
            and parts[-2] in {'co', 'com', 'org', 'net', 'ac', 'gov'}):
        return parts[-3]
    return parts[-2]


def _distinct_news(items, topic):
    out=[]; seen=set()
    for x in items or []:
        if not isinstance(x,dict) or not x.get('title') or not x.get('url') or not x.get('source'):
            continue
        host=_host(x.get('url'))
        if not host or not _topic_relevant(topic, x.get('title')):
            continue
        publisher=_publisher_key(host)
        if publisher in seen:
            continue
        seen.add(publisher); out.append(x)
    return out

def _sensitive(topic, news):
    text=' '.join([str(topic or '')]+[str(x.get('title') or '') for x in news or []])
    return bool(SENSITIVE_TREND_RE.search(text))

def sourced_topics(items, limit=5):
    ranked=[]; seen=set()
    for item in items or []:
        topic=' '.join(str(item.get('title') or '').split()).strip()
        news=_distinct_news(item.get('news') or [], topic)
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

def story_candidate(items, offset=0):
    """Pick one source-deep topic for a coherent long-form story."""
    topics=sourced_topics(items,limit=8)
    deep=[]
    for t in topics:
        # Long-form needs independent reporting even when the topic is not
        # sensitive; one headline is not enough substance for a deep story.
        if len(t.get('sources') or []) >= 2:
            deep.append(t)
    return deep[offset] if len(deep) > offset else None

def available(items, minimum=1):
    return len([t for t in sourced_topics(items, limit=8)
                if len(t.get('sources') or []) >= 2]) >= minimum

def build_plan(items, offset=0):
    t=story_candidate(items, offset=offset)
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
    plan=[]
    for i,(h,speech,visual,label,sub) in enumerate(beats,1):
        # The long-form contract is narration plus synchronized captions only.
        # Keep narrative beat metadata, but do not create visual scenes.
        plan.append(studio.scene(h,speech,'captions_only',label,sub,duration=12.0,
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
    caption_only=all(x.get('visual')=='captions_only' for x in plan)
    score+=10 if caption_only else -30
    report={'score':score,'beats':beats,'output_mode':'narration_with_synchronized_captions',
            'visual_scenes':False,'music':False,'source_count':len(sources)}
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
    """Static black frame with phrase captions; no scenes, motion graphics or overlays."""
    index=next((i for i,scene in enumerate(plan) if t<scene['end']),len(plan)-1)
    scene=plan[index]
    elapsed=t-scene['voice_start']
    audio_duration=len(scene['audio'])/studio.RATE
    im=Image.new('RGB',(1920,1080),(0,0,0))
    if elapsed < 0 or elapsed >= audio_duration:
        return im
    words=scene['speech'].split()
    if not words:
        return im
    # Captions advance proportionally through the generated narration segment.
    chunk_size=8
    chunk_count=math.ceil(len(words)/chunk_size)
    chunk=min(chunk_count-1,int((elapsed/audio_duration)*chunk_count))
    caption=' '.join(words[chunk*chunk_size:(chunk+1)*chunk_size])
    draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((145,390,1775,690),radius=28,fill=(12,12,12),
                           outline=(75,75,75),width=2)
    studio.fit_text(draw,caption,(205,435,1715,645),size=76,
                    fill=(255,255,255),align='center',max_lines=3)
    return im


def write_voice_only(plan,duration,path):
    """Write narration only: no music bed, stingers, transitions or effects."""
    count=int(math.ceil(duration*studio.RATE))
    voice=np.zeros(count,dtype=np.float32)
    for scene in plan:
        samples=np.asarray(scene['audio'],dtype=np.float32)
        start=int(round(float(scene['voice_start'])*studio.RATE))
        end=min(count,start+len(samples))
        if start<0 or end<=start:
            raise RuntimeError('Invalid narration timing in long-form plan.')
        voice[start:end]+=samples[:end-start]
    fade_in=np.clip(np.arange(count,dtype=np.float32)/(studio.RATE*.08),0,1)
    fade_out=np.clip((count-np.arange(count,dtype=np.float32))/(studio.RATE*.12),0,1)
    voice*=np.minimum(fade_in,fade_out)
    peak=float(np.max(np.abs(voice))) if count else 0.0
    if peak>0.94:
        voice*=0.94/peak
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(studio.RATE)
        output.writeframes((voice*32767).astype('<i2').tobytes())
    peak=max(float(np.max(np.abs(voice))) if count else 0.0,1e-9)
    return {'peak_dbfs':round(20*math.log10(peak),2),
            'voice':'Kokoro expressive profile','music':'none','sound_effects':'none'}


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
    # The evening edition must cover a different independently sourced topic.
    offset = 1 if str(episode_id).endswith('-pm') else 0
    plan,topics=build_plan(trend_items, offset=offset)
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
        audio_info=write_voice_only(plan,total,audio)
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
        'Narration with synchronized phrase captions only. No music, sound effects, motion graphics or illustrative scenes.'
    )
    report={
        'renderer':studio.VERSION,'format':'long','genre':'current','content_id':episode_id,
        'duration':round(total,3),'resolution':[1920,1080],'fps':studio.FPS,
        'scene_count':len(plan),'topic_count':1,'story_mode':'single-topic-deep-dive','audio':audio_info,
        'thumbnail':str(thumb),'sources':[s['url'] for x in topics for s in x.get('sources',[])],
        'creative_quality':quality,'output_mode':'narration_with_synchronized_captions',
        'visual_scenes':False,'music':False,'story_beats':[x.get('story_beat') for x in plan],
        'scenes':[{k:v for k,v in x.items() if k!='audio'} for x in plan],
    }
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Trend long-form complete:',json.dumps(report),flush=True)
    topic=topics[0]['topic'] if topics else 'Current Story'
    # Natural, topic-led packaging; distribution.py may refine this later from
    # measured search/browse evidence without adding unsupported claims.
    return f'Why {topic} Is Getting Attention Now | RAYVAN',description,report
