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
        host=str(x.get('publisher_domain') or '').lower().removeprefix('www.') or _host(x.get('url'))
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
                        'url':str(x['url'])[:1000],
                        'published':' '.join(str(x.get('published') or '').split())[:80],
                        'summary':' '.join(re.sub(r'<[^>]+>', ' ', str(x.get('summary') or '')).split())[:500]}
                       for x in chosen],
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

def _clean_summary(value, limit=420):
    """Normalize source-provided RSS context without treating it as verified fact."""
    return ' '.join(re.sub(r'<[^>]+>', ' ', str(value or '')).split())[:limit]


def _distinctive_thumbnail_copy(headline, topic):
    """Use a short, source-linked headline phrase rather than only the trend name."""
    words=re.findall(r"[A-Za-z0-9']+", str(headline or ''))
    if len(words) >= 3:
        return ' '.join(words[:7]).upper()[:58]
    return ' '.join(str(topic or 'CURRENT STORY').split()).upper()[:58]


def _retention_opening(headline, topic, source_name='', source_summary=''):
    """Open with a short source-provided detail and a question the episode will answer."""
    clean=' '.join(str(headline or topic or 'This story').split()).rstrip('.!?')
    headline_lead=' '.join(clean.split()[:9])
    summary=' '.join(_clean_summary(source_summary, limit=180).split()[:12])
    source=str(source_name or 'The linked report').strip()
    detail=(f'{source} reports: {summary}.' if summary else
            f'{source} is the starting point for this report.')
    return (f'{headline_lead}. {detail} What do the reports actually confirm about {topic}, '
            'and what remains unknown?')


def _retention_payoff(topic, source_summary):
    """Close the opening loop using only source-provided detail and explicit limits."""
    detail=_clean_summary(source_summary, limit=260)
    if not detail:
        detail='The available source record does not provide enough detail to confirm more.'
    return (f'So, what can we actually say about {topic}? The available report says: {detail}. '
            'That is the reported development. Anything beyond it remains unconfirmed until the full reports establish it.')


def retention_contract(plan):
    """Fail if the opening creates no question or the ending fails to resolve it."""
    if len(plan) < 3:
        raise RuntimeError('Retention contract rejected story: too few narrative beats.')
    opening=str(plan[0].get('speech') or '')
    ending=str(plan[-1].get('speech') or '')
    if '?' not in opening or len(opening.split()) > 45:
        raise RuntimeError('Retention contract rejected story: opening must establish a concise, explicit question.')
    if not all(token in ending.lower() for token in ('actually say', 'reported', 'unconfirmed')):
        raise RuntimeError('Retention contract rejected story: ending does not resolve the opening with evidence limits.')
    if opening == ending or len({x.get('story_beat') for x in plan}) < 6:
        raise RuntimeError('Retention contract rejected story: repetitive or insufficiently differentiated beats.')
    return {'opening_words':len(opening.split()),'closing_words':len(ending.split()),'distinct_beats':len({x.get('story_beat') for x in plan})}


def build_plan(items, offset=0):
    t=story_candidate(items, offset=offset)
    if not t:
        raise RuntimeError('No trend has enough independent source depth for a quality long-form story.')
    topic=t['topic']; headline=t['headline']; sources=t['source_names']
    source_rows=[]
    for source in (t.get('sources') or []):
        summary=_clean_summary(source.get('summary'))
        source_rows.append({
            'name':str(source.get('source') or 'Publisher')[:100],
            'published':str(source.get('published') or 'date not supplied')[:80],
            'summary':summary,
        })
    usable=[x for x in source_rows if x['summary']]
    if not usable:
        raise RuntimeError('Long-form story rejected: independent headlines exist, but no source summaries are available for substantive narration.')
    # Keep evidence readable aloud: use the two strongest available summaries,
    # with a strict per-source word budget instead of dumping the full RSS descriptions.
    source_rows=usable[:2]
    for row in source_rows:
        row['summary']=' '.join(row['summary'].split()[:32])
    evidence_line=' '.join(
        f"{x['name']} ({x['published']}): {x['summary']}" for x in source_rows
    )
    source_a=source_rows[0]
    source_b=source_rows[1] if len(source_rows)>1 else None
    second_line=(f"{source_b['name']} adds: {source_b['summary']}" if source_b else
                 "A second usable article summary is not available, so corroboration remains limited.")
    thumbnail_copy=_distinctive_thumbnail_copy(headline,topic)
    # Every beat has a different job: hook, catalyst, context, evidence,
    # cross-check, stakes, open question, and a bounded conclusion.
    beats=[
      ('THE DETAIL THAT STARTED IT',
       _retention_opening(headline, topic, source_a['name'], source_a['summary']),
       'signal',thumbnail_copy,'THE OPENING QUESTION'),
      ('WHAT THE REPORT ACTUALLY SAYS',
       f'The first linked report is from {source_a["name"]}. Its available summary says: {source_a["summary"]}. That is the concrete starting point; anything beyond it needs another source.',
       'screen','THE REPORTED DEVELOPMENT','THE CATALYST'),
      ('PUT THE HEADLINE IN CONTEXT',
       f'The trend chart tells us that people are searching for {topic}; it does not tell us why. The reporting context comes from {sources}. We should keep those two signals separate.',
       'map','SEARCH INTEREST ≠ PROOF','THE CONTEXT'),
      ('FOLLOW THE EVIDENCE',
       f'Here is the source-provided detail, in plain language: {evidence_line}. These are publisher summaries, not independently verified findings, so the linked reports remain the place to check the full context.',
       'evidence','WHAT THE SOURCES SAY','THE EVIDENCE'),
      ('CHECK WHAT THE SECOND REPORT ADDS',
       f'{second_line} Compare the details, dates and scope before treating the reports as agreement. If they do not establish the same point, the responsible conclusion is that the point remains unsettled.',
       'contrast','AGREEMENT OR OPEN QUESTION?','THE CROSS-CHECK'),
      ('WHY THE DISTINCTION MATTERS',
       f'For {topic}, the meaningful question is what this reported development could change if the details hold up. The available summaries do not establish every consequence, so we should not present a possible impact as an accomplished fact.',
       'impact','POSSIBLE CONSEQUENCE','THE STAKES'),
      ('WHAT STILL NEEDS CONFIRMING',
       f'The next useful update is specific: check the original linked reports for the full details, look for newer reporting from independent publishers, and see whether key dates or claims have changed. Until then, the unresolved parts stay unresolved.',
       'timeline','WHAT TO VERIFY NEXT','THE OPEN QUESTION'),
      ('THE TAKEAWAY',
       _retention_payoff(topic, source_a['summary']),
       'payoff','FOLLOW THE EVIDENCE','RAYVAN'),
    ]
    beat_names=['promise','catalyst','context','evidence','complication','implication','outlook','takeaway']
    visual_modes=['signal','evidence','map','evidence','contrast','impact','timeline','payoff']
    plan=[]
    for i,(h,speech,visual,label,sub) in enumerate(beats,1):
        plan.append(studio.scene(h,speech,visual_modes[i-1],label,sub,duration=12.0,
                                 section=i,source=t['source'],topic=topic,
                                 story_beat=beat_names[i-1]))
    topics=[dict(t, thumbnail_copy=thumbnail_copy)]
    return plan,topics

def long_quality_gate(plan,topics):
    if not plan or not topics: raise RuntimeError('Long-form creative gate: empty story.')
    beats=[x.get('story_beat') for x in plan]
    sources=topics[0].get('sources') or []
    score=45
    score+=min(20,len(set(beats))*3)
    summaries=[x for x in sources if len(_clean_summary(x.get('summary'))) >= 35]
    score+=15 if len(sources)>=2 else -30
    score+=10 if len(summaries)>=1 else -25
    score+=10 if {'promise','evidence','complication','implication','takeaway'}.issubset(set(beats)) else -20
    score+=10 if len(set(x.get('visual') for x in plan))>=5 else -15
    report={'score':score,'beats':beats,'visual_modes':[x.get('visual') for x in plan],
            'source_count':len(sources),'usable_summary_count':len(summaries)}
    if score<85: raise RuntimeError('Long-form creative gate rejected weak story: '+json.dumps(report))
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


def _thumbnail_style(topic):
    """Choose a topic-relevant vector motif without inventing a factual image."""
    value = str(topic or '').lower()
    groups = (
        (('space','planet','moon','mars','venus','solar','orbit','universe','nasa'), 'space', (111, 190, 255)),
        (('climate','weather','storm','flood','heat','earthquake','ocean','energy'), 'earth', (93, 220, 184)),
        (('money','business','bank','market','stock','economy','inflation','price'), 'economy', (255, 190, 92)),
        (('ai','artificial intelligence','robot','chip','technology','tech','computer','data'), 'technology', (190, 153, 255)),
        (('history','ancient','empire','war','king','civilization'), 'history', (255, 151, 126)),
        (('health','brain','body','science','medical','disease'), 'science', (112, 220, 226)),
    )
    for words, style, accent in groups:
        if any(word in value for word in words):
            return style, accent
    return 'signal', (114, 209, 255)


def _draw_thumbnail_hero(draw, style, accent):
    """Draw a bold, recognizable vector motif in the right-side hero area."""
    dark = (15, 34, 57)
    draw.ellipse((1190, 90, 1875, 775), fill=dark, outline=accent, width=7)
    if style == 'space':
        draw.ellipse((1390, 285, 1675, 570), fill=(31, 72, 112), outline=accent, width=8)
        draw.ellipse((1450, 345, 1615, 510), fill=(75, 125, 176))
        draw.ellipse((1280, 225, 1790, 625), outline=(111, 151, 190), width=5)
        draw.ellipse((1690, 260, 1730, 300), fill=(255, 224, 147))
    elif style == 'earth':
        draw.ellipse((1355, 250, 1715, 610), fill=(25, 105, 103), outline=accent, width=8)
        draw.arc((1390, 265, 1685, 595), 20, 155, fill=(190, 236, 218), width=9)
        draw.arc((1390, 265, 1685, 595), 200, 335, fill=(190, 236, 218), width=9)
        draw.line((1375, 430, 1695, 430), fill=(190, 236, 218), width=7)
    elif style == 'economy':
        for x, height in ((1330, 150), (1450, 245), (1570, 330), (1690, 430)):
            draw.rounded_rectangle((x, 650-height, x+82, 650), radius=16, fill=accent)
        draw.line((1310, 470, 1440, 385, 1560, 330, 1715, 205), fill=(255, 232, 184), width=12)
    elif style == 'technology':
        draw.rounded_rectangle((1390, 280, 1680, 570), radius=38, fill=(50, 43, 96), outline=accent, width=9)
        for offset in range(4):
            x = 1425 + offset*72
            draw.line((x, 225, x, 280), fill=accent, width=10)
            draw.line((x, 570, x, 625), fill=accent, width=10)
        draw.text((1535, 425), 'AI', font=studio.font(112), fill='white', anchor='mm')
    elif style == 'history':
        draw.polygon(((1335, 570), (1390, 335), (1535, 220), (1680, 335), (1735, 570)), fill=(96, 58, 50), outline=accent)
        for x in (1430, 1535, 1640):
            draw.rounded_rectangle((x-24, 365, x+24, 565), radius=8, fill=(236, 197, 153))
    elif style == 'science':
        draw.ellipse((1425, 320, 1645, 540), outline=accent, width=12)
        draw.ellipse((1480, 375, 1590, 485), fill=(67, 132, 157))
        draw.ellipse((1310, 285, 1760, 575), outline=(171, 218, 232), width=8)
        draw.ellipse((1508, 190, 1562, 244), fill=(255, 230, 153))
    else:
        draw.ellipse((1400, 295, 1670, 565), outline=accent, width=12)
        draw.line((1350, 430, 1720, 430), fill=accent, width=10)
        draw.line((1535, 245, 1535, 615), fill=accent, width=10)
        draw.ellipse((1490, 385, 1580, 475), fill=(255, 255, 255))


def thumbnail(path, topics):
    """Create a topic-led, mobile-readable 16:9 thumbnail with a distinct hero motif."""
    topic = ' '.join(str((topics[0] if topics else {}).get('topic') or 'CURRENT STORY').split())
    headline_copy = ' '.join(str((topics[0] if topics else {}).get('thumbnail_copy') or topic).split())
    style, accent = _thumbnail_style(topic)
    im = _background()
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((65, 65, 1090, 1015), radius=42, fill=(8, 19, 34), outline=(38, 68, 94), width=3)
    d.rounded_rectangle((105, 125, 125, 245), radius=9, fill=accent)
    d.text((165, 145), 'RAYVAN / EXPLAINED', font=studio.font(34), fill=(203, 220, 236))
    studio.fit_text(d, headline_copy, (115, 300, 1035, 785), size=112, fill='white', align='left', max_lines=4)
    d.text((115, 875), topic.upper()[:58], font=studio.font(25), fill=accent)
    _draw_thumbnail_hero(d, style, accent)
    im.resize((1280, 720), Image.Resampling.LANCZOS).save(path, 'JPEG', quality=94, optimize=True)


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
    quality['retention']=retention_contract(plan)
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
