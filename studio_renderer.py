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
from astra_errors import CreativeReject
import re
import subprocess
import tempfile
import wave
from functools import lru_cache

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from imageio_ffmpeg import get_ffmpeg_exe
from semantic_broll import infer_visual_intent
from character_animation import character_storyboard

VERSION = "studio-7.1.0"
W, H, FPS, RATE = 1080, 1920, 30, 24000
NEWS_MICRO_SCENE_SECONDS = 0.67
NEWS_MICRO_TRANSITION_SECONDS = 0.10
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
    "current": ((8, 13, 24), (18, 34, 54), (114, 209, 255)),
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


def _story_plan(ch):
    genre, cid = ch.get('genre', 'challenge'), ch.get('content_id', '')
    q, a = ch['question'].replace('\n', ' '), ch['answer'].replace('\n', ' ')
    # Premium stories carry their own editorial beat sheet. The renderer follows
    # the story rather than forcing the story into a reusable genre template.
    if ch.get('story_beats'):
        out=[]
        for raw in ch['story_beats']:
            item=dict(raw)
            out.append(scene(
                item.pop('headline'), item.pop('speech'), item.pop('visual'),
                item.pop('label',''), item.pop('sub',''), duration=item.pop('duration',0),
                **item
            ))
        return out
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
    if genre == 'current':
        source=(ch.get('news_source') or 'SOURCE').upper()[:28]
        source2=(ch.get('secondary_news_source') or 'SECOND SOURCE').upper()[:28]
        region=(ch.get('trend_region') or 'GLOBAL').upper()[:18]
        headline=' '.join(str(ch.get('news_title') or '').split())
        topic=' '.join(str(ch.get('topic') or headline or '').split())
        low=(topic+' '+headline+' '+q+' '+a).lower()

        def compact(text, words=16):
            parts=' '.join(str(text or '').split()).split()
            if len(parts)<=words:
                return ' '.join(parts).rstrip(' .,:;-')
            return (' '.join(parts[:words]).rstrip(' .,:;-')+'…')

        hook_line=compact(headline or ch.get('hook') or topic,12)
        research=[compact(x,18) for x in (ch.get('research_facts') or []) if str(x).strip()]
        while len(research)<2:
            research.append(compact(a,16))
        fact1,fact2=research[:2]

        beats=[
            scene(hook_line, compact(f"{topic}: {headline}",14), 'story_hook',
                  'NOW',source,duration=1.35,topic=topic,story_beat='reveal'),
            scene('FIRST VERIFIED DETAIL', fact1, 'story_evidence',
                  source,'SOURCE 1',duration=1.55,topic=topic,story_beat='evidence_primary'),
            scene('SECOND VERIFIED DETAIL', fact2, 'story_evidence',
                  source2,'SOURCE 2',duration=1.55,topic=topic,story_beat='evidence_secondary'),
        ]

        if re.search(r'vs\b|versus|match|game|playoff|score|player|team|cricket|wnba|nba|nhl|nfl|mlb|football|soccer|tennis',low):
            beats.append(scene('THE MATCHUP', compact(headline,14), 'story_context',
                               'MATCH CONTEXT',region,duration=1.45,topic=topic,story_beat='contrast'))
        elif re.search(r'country|city|state|island|border|travel|india|america|europe|asia|africa',low):
            beats.append(scene('WHERE IT FITS', compact(q,14), 'story_context',
                               'LOCATION / SCALE',region,duration=1.45,topic=topic,story_beat='map'))
        elif re.search(r'why|because|how|technology|science|system|process|works|effect|cause|behind',low):
            beats.append(scene('WHY IT IS HAPPENING', compact(q,14), 'story_context',
                               'THE MECHANISM',topic[:28].upper(),duration=1.45,topic=topic,story_beat='mechanism'))
        else:
            beats.append(scene('THE CONTEXT', compact(q,14), 'story_context',
                               'WHAT CHANGED',region,duration=1.45,topic=topic,story_beat='context'))

        beats.extend([
            scene('WHY IT MATTERS', compact(a,16), 'story_context',
                  'THE CONSEQUENCE',region,duration=1.55,topic=topic,story_beat='consequence'),
            scene('WHAT TO WATCH', 'Details can still change. Follow the verified sources for the next confirmed update.',
                  'story_evidence','VERIFY NEXT',source,duration=1.35,topic=topic,story_beat='uncertainty'),
            scene('THE TAKEAWAY', compact(a,13), 'story_outlook',
                  'WHAT TO REMEMBER','RAYVAN / STORIES BEYOND THE ORDINARY',
                  duration=1.35,topic=topic,story_beat='payoff'),
        ])
        return beats[:8]
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



def direct_story(ch, plan):
    """Automated director: derive a shot grammar from meaning, not a fixed template."""
    topic=str(ch.get('topic') or ch.get('title') or '')
    source_count=int(ch.get('source_count') or 0)
    directed=[]
    for i,raw in enumerate(plan):
        shot=dict(raw)
        text=' '.join(str(shot.get(k,'')) for k in ('headline','speech','label','sub'))+' '+topic
        low=text.lower()
        semantics=[]
        tests=[
          ('person',r'president|senator|minister|actor|singer|player|ceo|people|election|politic'),
          ('map',r'country|city|state|island|border|travel|india|america|europe|asia|africa'),
          ('clock',r'time|daylight|clock|date|year|month|week|hour|schedule'),
          ('network',r'\bai\b|technology|software|chip|computer|phone|internet|science'),
          ('compare',r'market|stock|price|money|company|business|sales|economy|versus|more than|less than'),
          ('evidence',r'source|report|evidence|according|what we know|verified'),
          ('future',r'next|watch|develop|future|comes next'),
        ]
        for name,pat in tests:
            if re.search(pat,low): semantics.append(name)
        # Story architecture is authoritative: visual meaning follows the beat,
        # rather than depending on lucky keywords in narration.
        beat=shot.get('story_beat','')
        beat_semantic={'map':'map','mechanism':'network','contrast':'compare',
                       'evidence':'evidence','evidence_primary':'evidence',
                       'evidence_secondary':'evidence','uncertainty':'evidence',
                       'consequence':'future'}.get(beat)
        if beat_semantic and beat_semantic not in semantics:
            semantics.insert(0,beat_semantic)
        # Narrative role controls editing rhythm. The same semantic subject can
        # therefore be photographed/animated differently at different beats.
        if i==0: role='cold_open'
        elif i==len(plan)-1: role='resolution'
        elif 'evidence' in semantics: role='proof'
        elif 'future' in semantics: role='outlook'
        elif i<=len(plan)//2: role='build'
        else: role='payoff'
        energy={'cold_open':1.0,'build':.68,'proof':.52,'payoff':.88,'outlook':.62,'resolution':.45}[role]
        # Deterministic shot variation prevents every story from inheriting the
        # same composition while keeping renders reproducible for CI.
        seed=int(hashlib.sha256((topic+text+str(i)).encode()).hexdigest()[:8],16)
        shot.update(director_role=role,director_energy=energy,
                    director_semantics=semantics,
                    director_camera=['push','drift','reveal','track'][seed%4],
                    director_layout=['focus-left','focus-right','center','split'][seed%4],
                    director_pattern_interrupt=(i>0 and role in {'proof','payoff','outlook'}),
                    director_source_depth=source_count,
                    director_motion=['arc','scan','pulse','parallax'][seed%4],
                    director_cut_rate=round(.55 + energy*.75,2),
                    director_caption_mode=('question' if role=='cold_open' and '?' in str(shot.get('speech','')) else 'phrase'),
                    director_style=(
                        'mixed-media' if role=='proof' else
                        'vector-motion' if any(x in semantics for x in ('map','compare','network')) else
                        'cel-shaded' if role in {'cold_open','payoff'} and energy>=.85 else
                        'stylized-cgi' if role in {'cold_open','outlook'} else
                        'stop-motion' if role=='build' and seed%3==0 else
                        'mixed-media'
                    ),
                    director_asset=(
                        'map-explainer' if beat=='map' else
                        'mechanism-diagram' if beat=='mechanism' else
                        'comparison-graphic' if beat=='contrast' else
                        'source-document' if beat in ('evidence','uncertainty') and source_count>0 else
                        'editorial-illustration' if beat in ('reveal','consequence','payoff') else
                        'source-document' if role=='proof' and source_count>0 else
                        'map-explainer' if 'map' in semantics else
                        'mechanism-diagram' if 'network' in semantics else
                        'comparison-graphic' if 'compare' in semantics else
                        'time-visualization' if 'clock' in semantics else
                        'editorial-illustration' if 'person' in semantics else
                        'kinetic-type'
                    ))
        if ch.get('genre')=='current':
            story_text=' '.join(str(ch.get(k) or '') for k in ('topic','news_title','question','answer')).lower()
            sports_news=bool(re.search(r'wnba|nba|nhl|nfl|mlb|cricket|football|soccer|tennis|match|playoff|score|player|team|\bvs\b|game preview',story_text))
            beat=str(shot.get('story_beat') or '')
            if sports_news:
                asset_map={
                    'reveal':'sports-matchup-card',
                    'evidence_primary':'source-document',
                    'evidence_secondary':'source-document',
                    'contrast':'sports-score-context',
                    'context':'sports-context-card',
                    'map':'sports-context-card',
                    'mechanism':'sports-play-diagram',
                    'consequence':'timeline-graphic',
                    'uncertainty':'source-document',
                    'payoff':'sports-takeaway-card',
                }
            else:
                asset_map={
                    'reveal':'news-headline-card',
                    'evidence_primary':'source-document',
                    'evidence_secondary':'source-document',
                    'contrast':'comparison-graphic',
                    'context':'news-context-card',
                    'map':'map-explainer',
                    'mechanism':'mechanism-diagram',
                    'consequence':'timeline-graphic',
                    'uncertainty':'source-document',
                    'payoff':'news-takeaway-card',
                }
            shot['director_asset']=asset_map.get(beat,shot.get('director_asset'))
            shot['director_motion']=['glide','scan','parallax','glide','arc','scan','glide','parallax'][i % 8]
            shot['director_camera']=['push','drift','track','reveal','push','drift','track','push'][i % 8]
            shot['director_layout']=['center','focus-left','focus-right','split','center','focus-left','focus-right','center'][i % 8]
        semantic_broll=infer_visual_intent(shot,i)
        shot["semantic_broll"]=semantic_broll
        # For generic beats, meaning-first B-roll intent can strengthen the
        # director without overriding explicit evidence/map/mechanism grammar.
        if shot.get("director_asset")=="kinetic-type":
            vt=semantic_broll.get("visual_type")
            if vt=="compare":
                shot["director_asset"]="comparison-graphic"
            elif vt=="map":
                shot["director_asset"]="map-explainer"
            elif vt=="mechanism":
                shot["director_asset"]="mechanism-diagram"
            elif vt=="data":
                shot["director_asset"]="time-visualization"
        directed.append(shot)
    return directed

def make_plan(ch):
    # Studio 7 routes each story into a distinct visual grammar instead of
    # forcing every Short through one recurring composition.
    plan = direct_story(ch, _story_plan(ch))
    from creative_formats import choose_format, apply_format
    fmt = choose_format(ch, recent_formats=ch.get("recent_formats") or [])
    ch["creative_format"] = fmt["name"]
    return apply_format(plan, fmt)


def voice_plan(plan, genre, max_duration=59, voice_name='af_heart', voice_speed=1.09):
    engine=voice_engine()
    cursor=0.0
    for s in plan:
        spoken=str(s['speech']).strip()
        # Natural cadence wins over synthetic "news voice" punctuation tricks.
        spoken=spoken.replace('; ', '. ').replace('  ',' ')
        samples, rate=engine.create(spoken,voice=voice_name,speed=voice_speed,lang='en-us')
        samples=np.asarray(samples,dtype=np.float32)
        if rate!=RATE or len(samples)==0 or not np.isfinite(samples).all():
            raise RuntimeError('Invalid narration audio; refusing to publish an incomplete video.')
        # Normalize each line gently, then mix with a substantially quieter score.
        peak=float(np.max(np.abs(samples)))
        if peak>0: samples=samples*(.65/peak)
        s.update(audio=samples,start=cursor,voice_start=cursor+.08,
                 duration=max(float(s['min_duration']),len(samples)/RATE+.24))
        s['end']=s['start']+s['duration']
        cursor=s['end']
    if cursor>max_duration:
        # Dynamic stories can create more useful beats than the Shorts budget allows.
        # First compress dead air; if narration alone still cannot fit, remove the
        # lowest-priority optional beat and regenerate timing without touching
        # reveal/evidence/payoff. This is editorial compression, not truncation.
        protected={'reveal','evidence','payoff'}
        while cursor>max_duration:
            voice_total=sum(len(x['audio'])/RATE for x in plan)
            min_total=sum(len(x['audio'])/RATE+.10 for x in plan)
            if min_total<=max_duration:
                overhead=max(0.0,cursor-voice_total)
                target_overhead=max(0.0,max_duration-voice_total-.05)
                ratio=min(1.0,target_overhead/max(.001,overhead))
                cursor=0.0
                for x in plan:
                    voice_len=len(x['audio'])/RATE
                    hold=max(voice_len+.10,voice_len+max(0.0,x['duration']-voice_len)*ratio)
                    x.update(start=cursor,voice_start=cursor+.06,duration=hold,end=cursor+hold)
                    cursor+=hold
                break
            optional=[(i,x) for i,x in enumerate(plan)
                      if x.get('story_beat') not in protected and x.get('story_beat')!='cta']
            if not optional: break
            priority={'contrast':0,'map':1,'mechanism':2,'consequence':3,'uncertainty':4}
            drop_i,_=min(optional,key=lambda z:priority.get(z[1].get('story_beat'),5))
            plan.pop(drop_i)
            cursor=0.0
            for x in plan:
                voice_len=len(x['audio'])/RATE
                x.update(start=cursor,voice_start=cursor+.10,duration=voice_len+.18,end=cursor+voice_len+.18)
                cursor=x['end']
    # Fail before frame encoding: the publishing contract requires a full
    # 55-59 second Short. Do not stretch sparse narration into dead air.
    minimum_duration = 55.0
    if not minimum_duration <= cursor <= max_duration:
        raise RuntimeError(
            f'Video narration duration {cursor:.1f}s outside publishable '
            f'{minimum_duration:.0f}-{max_duration:.0f}s; '
            'revise the script and render again.')
    return cursor


def score_audio(plan, duration, genre, path):
    """Procedural music, voice-aware ducking, stereo motion and soft transition hits."""
    n=int(math.ceil(duration*RATE)); t=np.arange(n,dtype=np.float32)/RATE
    rng=np.random.default_rng(2104)
    # Rounded synthesizer tones; different harmonic palette for each series.
    root={'space':146.832,'fiction':130.813,'tech':164.814,'football':146.832,'challenge':164.814,'current':155.563}[genre]
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
    music=(kick+melody+pad)*.18
    duck=np.ones(n,dtype=np.float32)
    speech=np.zeros(n,dtype=np.float32); fx=np.zeros(n,dtype=np.float32)
    for s in plan:
        j=int(s['voice_start']*RATE); b=s['audio']; end=min(n,j+len(b))
        speech[j:end]+=b[:end-j]*1.08
        # Smooth 80 ms attack/release on music ducking; no pumping on every word.
        idx=np.arange(n,dtype=np.float32)/RATE
        env=np.minimum(np.clip((idx-s['voice_start']+.08)/.08,0,1),np.clip((s['voice_start']+len(b)/RATE+.12-idx)/.12,0,1))
        duck=np.minimum(duck,1-.70*env)
        k=int(s['start']*RATE); size=min(int(.24*RATE),n-k)
        u=np.arange(size,dtype=np.float32)/RATE
        noise=rng.normal(0,1,size).astype(np.float32)
        noise=np.convolve(noise,np.ones(12)/12,mode='same')
        fx[k:k+size]+=noise*np.sin(np.pi*np.arange(size)/max(1,size))*.025
        # Attention transient: strongest on the opening beat, lighter thereafter.
        hit=.055 if s.get('start',0)<.1 else .032
        fx[k:k+size]+=np.sin(2*np.pi*(110+420*u)*u)*np.exp(-u*18)*hit
        if s.get('answer'):
            fx[k:k+size]+=np.sin(2*np.pi*880*u)*np.exp(-u*14)*.035
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
    if peak>.94: mixed*=.94/peak
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes((mixed*32767).astype('<i2').tobytes())
    return {'peak_dbfs':round(20*math.log10(max(float(np.max(np.abs(mixed))),1e-9)),2),'voice':'Kokoro expressive profile','music':'subtle procedural bed'}


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
    for x,y,r,phase in zip(rng.integers(45,1035,65),rng.integers(475,1330,65),rng.integers(1,4,65),rng.random(65)):
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
    elif visual=='media':
        # Media is the scene, not a card inside a template.
        pass
    elif visual=='tidal_lock':
        # Purpose-built synchronous-rotation demonstration: a marked point on
        # the Moon always faces Earth while the Moon completes an orbit.
        d.ellipse((150,590,930,1160),outline=(70,82,112),width=4)
        ex,ey=540,875
        d.ellipse((ex-105,ey-105,ex+105,ey+105),fill=(54,113,171),outline=(173,215,246),width=4)
        d.text((ex,ey),'EARTH',font=font(26),anchor='mm',fill='white')
        phase=min(1.0,max(0.0,u/max(.2,s.get('duration',3.5))))
        ang=-math.pi/2 + phase*2*math.pi
        rx,ry=390,285
        mx,my=ex+rx*math.cos(ang),ey+ry*math.sin(ang)
        r=78
        d.ellipse((mx-r,my-r,mx+r,my+r),fill=(184,190,199),outline=(245,247,250),width=4)
        # Marker is placed on the hemisphere pointing toward Earth.
        vx,vy=ex-mx,ey-my
        mag=max(1.0,math.hypot(vx,vy)); vx,vy=vx/mag,vy/mag
        markx,marky=mx+vx*48,my+vy*48
        d.ellipse((markx-15,marky-15,markx+15,marky+15),fill=accent,outline='white',width=3)
        d.line((mx,my,markx,marky),fill=accent,width=5)
        # Orbit direction and the one-to-one relationship are the only labels.
        d.arc((130,570,950,1180),205,330,fill=accent,width=7)
        d.polygon([(902,1074),(928,1037),(883,1041)],fill=accent)
        d.rounded_rectangle((250,1210,830,1305),radius=26,fill=(8,12,23))
        fit_text(d,'1 ORBIT  =  1 SPIN',(278,1228,802,1287),size=39,fill='white',max_lines=1)
    elif visual=='iss_orbit':
        d=ImageDraw.Draw(im)
        ex,ey=540,875
        d.ellipse((145,590,935,1160),outline=(70,82,112),width=4)
        d.ellipse((ex-105,ey-105,ex+105,ey+105),fill=(54,113,171),outline=(173,215,246),width=4)
        d.text((ex,ey),'EARTH',font=font(26),anchor='mm',fill='white')
        phase=min(1.0,max(0.0,u/max(.2,s.get('duration',3.5))))
        ang=-math.pi/2 + phase*2*math.pi
        sx,sy=ex+395*math.cos(ang),ey+285*math.sin(ang)
        d.rounded_rectangle((sx-60,sy-18,sx+60,sy+18),radius=8,fill=(221,226,234),outline='white',width=2)
        d.rectangle((sx-125,sy-12,sx-66,sy+12),fill=(73,118,190))
        d.rectangle((sx+66,sy-12,sx+125,sy+12),fill=(73,118,190))
        d.arc((125,570,955,1180),205,330,fill=accent,width=7)
        d.rounded_rectangle((250,1210,830,1305),radius=26,fill=(8,12,23))
        fit_text(d,'~90 MINUTES / ORBIT',(278,1228,802,1287),size=39,fill='white',max_lines=1)
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



def _semantic_tokens(s):
    text=' '.join(str(s.get(k,'')) for k in ('topic','headline','speech','label','sub')).lower()
    groups={
      'people':r'president|senator|minister|actor|singer|player|ceo|person|people|opposition|election|politic',
      'place':r'country|city|state|island|border|travel|location|india|america|europe|asia|africa',
      'time':r'time|daylight|clock|date|year|month|week|hour|schedule',
      'tech':r'ai|technology|software|chip|computer|phone|robot|science|internet|app',
      'money':r'market|stock|price|money|company|business|sales|economy|deal',
    }
    return [k for k,p in groups.items() if re.search(p,text)]

def attention_layer(im,s,t,u,accent):
    """Meaning-driven animated overlays. These compose per story rather than pick a template."""
    d=ImageDraw.Draw(im,'RGBA'); tokens=_semantic_tokens(s)
    if 'time' in tokens:
        cx,cy=790,720;r=145;d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=accent+(165,),width=8)
        a=-math.pi/2+t*1.8;d.line((cx,cy,cx+math.cos(a)*r*.72,cy+math.sin(a)*r*.72),fill=(255,255,255,225),width=12)
        d.ellipse((cx-13,cy-13,cx+13,cy+13),fill=accent+(255,))
    if 'people' in tokens:
        x=205+int(24*math.sin(t*.8));y=840
        d.ellipse((x-55,y-205,x+55,y-95),fill=accent+(125,))
        d.rounded_rectangle((x-105,y-82,x+105,y+165),34,fill=accent+(72,))
    if 'place' in tokens:
        for j in range(3):
            rr=80+j*55+int(8*math.sin(t*2+j))
            d.arc((530-rr,790-rr,530+rr,790+rr),200,345,fill=accent+(150-j*30,),width=7)
        d.ellipse((516,776,544,804),fill=(255,255,255,235))
    if 'tech' in tokens:
        pts=[(170,700),(345,590),(550,735),(750,575),(875,805)]
        for a,b in zip(pts,pts[1:]):d.line((*a,*b),fill=accent+(110,),width=6)
        for x,y in pts:d.ellipse((x-17,y-17,x+17,y+17),fill=accent+(225,))
    if 'money' in tokens:
        for j,v in enumerate((.35,.62,.48,.82,.70)):
            x=165+j*150;h=int(300*v*(.82+.18*ease(u)))
            d.rounded_rectangle((x,970-h,x+80,970),15,fill=accent+(100+j*20,))
    if u<.18:
        alpha=int(200*(1-u/.18));d.rectangle((0,310,W,322),fill=accent+(alpha,))
    return im




def visual_style_layer(im,s,t,u,accent):
    """Original RAYVAN visual languages: CGI-like depth, toon, vector, mixed media, tactile stop-motion."""
    d=ImageDraw.Draw(im,'RGBA'); style=s.get('director_style','mixed-media')
    if style=='stylized-cgi':
        # Layered pseudo-3D geometry with moving highlights/depth.
        for j in range(5):
            z=1+j*.18; x=int(130+j*165+math.sin(t*.7+j)*28); y=int(690+j*78)
            r=int((72+18*j)*z)
            d.rounded_rectangle((x-r,y-r,x+r,y+r),int(24*z),
                                fill=(18+8*j,28+9*j,48+12*j,185),outline=accent+(125,),width=5)
            d.ellipse((x-r//2,y-r//2,x+r//3,y+r//3),fill=(255,255,255,28))
    elif style=='cel-shaded':
        # Flat graphic planes + bold contour language, not an imitation of any studio.
        pts=[(95,1040),(250,650),(470,780),(690,570),(985,900),(985,1190),(95,1190)]
        d.polygon(pts,fill=accent+(65,))
        d.line(pts+[pts[0]],fill=(8,10,18,230),width=18,joint='curve')
        for off in (0,55,110):
            d.line((120+off,1130,450+off,760),fill=(255,255,255,70),width=9)
    elif style=='vector-motion':
        # Crisp vector shapes with meaningful motion rhythm.
        for j in range(7):
            a=t*.45+j*.9; x=540+int(math.cos(a)*260); y=860+int(math.sin(a)*210)
            rr=22+(j%3)*9
            d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=accent+(110+j*12,),outline=(255,255,255,100),width=3)
            if j: d.line((540,860,x,y),fill=accent+(65,),width=5)
    elif style=='mixed-media':
        # Paper/card collage layers around live/real media or evidence graphics.
        for j,(x,y,w,h) in enumerate(((105,620,320,170),(650,690,300,190),(155,1010,390,150))):
            ang=math.sin(t*.35+j)*6
            d.rounded_rectangle((x,y,x+w,y+h),20,fill=(245,238,220,35+j*12),
                                outline=(255,255,255,45),width=4)
        d.line((100,970,960,970),fill=accent+(95,),width=4)
    elif style=='stop-motion':
        # Tactile cut-paper/puppet-like forms with stepped motion.
        step=int(t*8); jitter=((step%3)-1)*5
        for j in range(4):
            x=180+j*205+jitter*(1 if j%2 else -1); y=790+(j%2)*125
            d.rounded_rectangle((x-72,y-72,x+72,y+72),34,fill=(210,190-15*j,155+15*j,185),
                                outline=(25,25,28,180),width=7)
            d.ellipse((x-24,y-18,x-10,y-4),fill=(20,20,22,180))
            d.ellipse((x+10,y-18,x+24,y-4),fill=(20,20,22,180))
    return im

def asset_layer(im,s,t,u,accent):
    """Render the director's story-specific asset choice with provenance-safe fallbacks."""
    d=ImageDraw.Draw(im,'RGBA'); kind=s.get('director_asset','kinetic-type')
    if kind=='source-document':
        x0,y0,x1,y1=150,610,900,1070
        d.rounded_rectangle((x0,y0,x1,y1),30,fill=(245,247,250,235),outline=accent+(190,),width=5)
        d.rectangle((x0+55,y0+60,x0+320,y0+84),fill=accent+(180,))
        for j,w in enumerate((610,540,590,430,515)):
            yy=y0+135+j*54; d.rounded_rectangle((x0+55,yy,x0+55+w,yy+16),8,fill=(40,50,65,95))
        # Explicitly label this as a source abstraction; never fake a screenshot.
        d.text((x0+55,y1-78),'SOURCE / EVIDENCE',font=font(28),fill=(28,38,52,220))
    elif kind=='map-explainer':
        pts=[(160,900),(300,710),(475,790),(620,640),(860,770)]
        d.line(pts,fill=accent+(170,),width=9)
        for j,(x,y) in enumerate(pts):
            rr=18 if j not in {0,len(pts)-1} else 28
            d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=accent+(220,))
    elif kind=='mechanism-diagram':
        nodes=[(200,760),(440,650),(440,900),(760,760)]
        for a,b in ((0,1),(0,2),(1,3),(2,3)):
            d.line((*nodes[a],*nodes[b]),fill=accent+(135,),width=8)
        for j,(x,y) in enumerate(nodes):
            r=48 if j in {0,3} else 36
            d.ellipse((x-r,y-r,x+r,y+r),fill=(12,22,38,220),outline=accent+(220,),width=6)
    elif kind=='comparison-graphic':
        for j,(name,v) in enumerate((('A',.58),('B',.88))):
            y=720+j*190; d.text((150,y),name,font=font(45),fill=(255,255,255,225))
            d.rounded_rectangle((240,y,900,y+70),35,fill=(30,42,60,190))
            d.rounded_rectangle((240,y,240+int(660*v*ease(min(1,u/.7))),y+70),35,fill=accent+(190,))
    elif kind=='time-visualization':
        # Clock semantics are already animated by attention_layer; add a timeline cue.
        d.line((145,1030,900,1030),fill=accent+(145,),width=7)
        for x in (180,420,660,860): d.ellipse((x-13,1017,x+13,1043),fill=(255,255,255,220))
    elif kind=='sports-matchup-card':
        d.rounded_rectangle((115,650,965,1050),38,fill=(10,18,32,225),outline=accent+(190,),width=6)
        d.text((150,700),'MATCHUP',font=font(34),fill=accent+(230,))
        d.line((540,760,540,980),fill=(255,255,255,70),width=4)
        d.text((245,860),'SIDE A',font=font(48),fill=(255,255,255,230),anchor='mm')
        d.text((835,860),'SIDE B',font=font(48),fill=(255,255,255,230),anchor='mm')
        d.text((540,860),'VS',font=font(44),fill=accent+(235,),anchor='mm')
    elif kind=='sports-score-context':
        d.rounded_rectangle((130,680,950,1040),34,fill=(14,22,38,225),outline=accent+(180,),width=5)
        d.text((175,730),'GAME CONTEXT',font=font(32),fill=accent+(230,))
        for j,(label,val) in enumerate((('FORM',.68),('MOMENTUM',.82),('PRESSURE',.74))):
            y=810+j*72
            d.text((175,y),label,font=font(25),fill=(235,240,248,215))
            d.rounded_rectangle((405,y+5,870,y+35),15,fill=(40,52,70,190))
            d.rounded_rectangle((405,y+5,405+int(465*val*ease(min(1,u/.65))),y+35),15,fill=accent+(185,))
    elif kind=='sports-context-card':
        d.rounded_rectangle((140,690,940,1050),34,fill=(16,24,40,220),outline=accent+(165,),width=5)
        d.text((190,750),'STORY CONTEXT',font=font(30),fill=accent+(220,))
        d.line((190,850,880,850),fill=(255,255,255,60),width=4)
        for j,x in enumerate((250,470,690,850)):
            rr=16+int(5*math.sin(t*2+j))
            d.ellipse((x-rr,850-rr,x+rr,850+rr),fill=accent+(210,))
    elif kind=='sports-play-diagram':
        d.rounded_rectangle((120,620,960,1100),40,fill=(18,48,36,220),outline=(255,255,255,70),width=4)
        d.line((540,650,540,1070),fill=(255,255,255,70),width=4)
        for x,y in ((260,760),(390,900),(700,760),(820,930)):
            d.ellipse((x-26,y-26,x+26,y+26),outline=accent+(230,),width=6)
        x2=int(285+(375*ease(min(1,u/.8))))
        d.line((285,780,x2,790),fill=accent+(180,),width=6)
        d.polygon([(x2,790),(x2-34,770),(x2-31,815)],fill=accent+(220,))
    elif kind=='timeline-graphic':
        d.text((145,690),'WHAT HAPPENED',font=font(32),fill=accent+(220,))
        d.line((180,820,900,820),fill=accent+(160,),width=8)
        p=ease(min(1,u/.75))
        for j,x in enumerate((220,460,700,860)):
            if p >= j/4:
                r=19 if j<3 else 27
                d.ellipse((x-r,820-r,x+r,820+r),fill=accent+(220,))
                d.text((x,900),str(j+1),font=font(24),fill=(255,255,255,210),anchor='mm')
    elif kind=='sports-takeaway-card':
        d.rounded_rectangle((125,700,955,1060),38,fill=(12,20,34,230),outline=accent+(190,),width=6)
        d.text((170,765),'THE TAKEAWAY',font=font(34),fill=accent+(230,))
        d.line((170,835,890,835),fill=(255,255,255,65),width=4)
        d.text((540,930),'WHAT MATTERS NEXT',font=font(46),fill=(255,255,255,230),anchor='mm')
    elif kind=='news-headline-card':
        d.rounded_rectangle((120,650,960,1050),40,fill=(12,18,30,235),outline=accent+(180,),width=6)
        d.text((165,710),'DEVELOPING',font=font(32),fill=accent+(225,))
        d.line((165,790,900,790),fill=(255,255,255,65),width=4)
        w=int(700*ease(min(1,u/.7)))
        d.rounded_rectangle((165,860,165+w,900),18,fill=accent+(150,))
        d.rounded_rectangle((165,930,165+int(w*.78),966),18,fill=(255,255,255,65))
    elif kind=='news-context-card':
        d.rounded_rectangle((130,690,950,1050),36,fill=(14,22,38,225),outline=accent+(170,),width=5)
        d.text((175,745),'CONTEXT',font=font(32),fill=accent+(225,))
        for j,w in enumerate((610,520,680)):
            yy=835+j*65
            d.rounded_rectangle((175,yy,175+int(w*ease(min(1,u/.7))),yy+22),11,fill=(235,240,248,75+j*20))
    elif kind=='news-takeaway-card':
        d.rounded_rectangle((125,700,955,1060),38,fill=(12,20,34,230),outline=accent+(190,),width=6)
        d.text((170,765),'THE TAKEAWAY',font=font(34),fill=accent+(230,))
        d.line((170,835,890,835),fill=(255,255,255,65),width=4)
        d.text((540,930),'VERIFIED • COMPACT • CURRENT',font=font(34),fill=(255,255,255,220),anchor='mm')
    elif kind=='editorial-illustration':
        # Abstract only: never imply a generated likeness is the real person.
        d.text((145,1040),'EDITORIAL CONTEXT',font=font(25),fill=accent+(180,))
    return im

def director_motion_layer(im,s,t,u,accent):
    """Micro-animation selected by the director; adds depth without a reusable scene template."""
    d=ImageDraw.Draw(im,'RGBA')
    mode=s.get('director_motion','pulse'); energy=float(s.get('director_energy',.5))
    if mode=='scan':
        y=int(560+(u*260*max(.5,energy))%500)
        d.rectangle((90,y,930,y+3),fill=accent+(95,))
    elif mode=='arc':
        r=220+int(35*math.sin(t*2.1))
        d.arc((540-r,760-r,540+r,760+r),int(t*45)%360,int(t*45)%360+105,fill=accent+(110,),width=5)
    elif mode=='pulse':
        r=90+int((u*120)%190)
        d.ellipse((540-r,780-r,540+r,780+r),outline=accent+(max(25,120-r//3),),width=5)
    elif mode=='parallax':
        for j in range(5):
            x=int((120+j*220+t*(10+5*j)*energy)%1180)-50
            d.ellipse((x,650+j*70,x+16,666+j*70),fill=accent+(55+j*18,))
    elif mode=='glide':
        phase=t*.9
        xoff=int(math.sin(phase)*45*energy)
        yoff=int(math.cos(phase*.72)*18*energy)
        d.rounded_rectangle((100+xoff,620+yoff,980+xoff,1120+yoff),44,
                            outline=accent+(48,),width=5)
    return im



def composition_layer(im,s,t,u,accent):
    """Director-controlled staging with foreground/midground/background depth."""
    d=ImageDraw.Draw(im,'RGBA')
    layout=s.get('director_layout','center')
    enter=ease(min(1,u/.18))
    # Background depth plane: slowest movement.
    bgx=int(math.sin(t*.18)*18)
    d.ellipse((70+bgx,500,1010+bgx,1440),fill=accent+(16,))
    # Midground subject card follows actual director layout.
    centers={'focus-left':300,'focus-right':780,'center':540,'split':350}
    cx=centers.get(layout,540)
    direction=-1 if cx<540 else 1
    cx+=int(direction*(1-enter)*230)
    cy=870+int(math.sin(t*.45)*12)
    d.rounded_rectangle((cx-185,cy-145,cx+185,cy+145),36,
                        fill=(12,18,30,78),outline=accent+(72,),width=5)
    if layout=='split':
        cx2=730-int((1-enter)*190)
        d.rounded_rectangle((cx2-150,cy-115,cx2+150,cy+115),30,
                            fill=(255,255,255,24),outline=(255,255,255,52),width=4)
        d.line((540,650,540,1120),fill=accent+(55,),width=4)
    # Foreground accents move fastest, creating parallax/depth.
    fg=int(math.sin(t*.7)*42)
    d.polygon([(0,1460+fg),(250,1370+fg),(390,1920),(0,1920)],fill=accent+(28,))
    d.polygon([(1080,1390-fg),(860,1340-fg),(720,1920),(1080,1920)],fill=(255,255,255,18))
    return im

def transition_layer(im,s,t,u,accent):
    """Narrative-energy transition treatment concentrated at scene entry/exit."""
    d=ImageDraw.Draw(im,'RGBA'); energy=float(s.get('director_energy',.5))
    if u<.20:
        p=ease(u/.20); w=int((1-p)*W*.34*energy)
        if w>0:
            d.polygon([(0,0),(w,0),(max(0,w-120),H),(0,H)],fill=accent+(max(0,int(95*(1-p))),))
    elif u>.84 and s.get('director_role') in {'proof','payoff','outlook','resolution'}:
        p=ease((u-.84)/.16); y=int(H-(p*110))
        d.rectangle((0,y,W,H),fill=(255,255,255,max(0,int(22*(1-p)))))
    return im

def _micro_scene_direction(shot, t, genre):
    """Change visual direction during narration without cutting its audio.

    Fiction gets a stable story-specific sequence of one-second shot treatments,
    rather than holding one camera composition for an entire spoken beat.
    This is procedural cinematography, NOT AI-generated animation.
    """
    if genre not in {'current', 'fiction'}:
        return shot, None
    interval = NEWS_MICRO_SCENE_SECONDS if genre == 'current' else 1.0
    micro_index = max(0, int(t / interval))
    phase = (t % interval) / interval
    x = dict(shot)
    cameras = ('push', 'track', 'drift')
    layouts = ('center', 'focus-left', 'focus-right', 'split')
    motions = ('glide', 'scan', 'parallax', 'arc', 'pulse')
    styles = ('mixed-media', 'vector-motion', 'cel-shaded', 'stop-motion')
    if genre == 'fiction':
        identity = '|'.join(str(shot.get(key) or '') for key in
                            ('headline', 'visual', 'story_beat', 'speech'))
        offset = int(hashlib.sha256(identity.encode('utf-8')).hexdigest()[:8], 16)
    else:
        offset = 0
    x['director_camera'] = cameras[(micro_index + offset) % len(cameras)]
    x['director_layout'] = layouts[(micro_index + offset // 3) % len(layouts)]
    x['director_motion'] = motions[(micro_index + offset // 7) % len(motions)]
    if x.get('director_asset') != 'source-document':
        x['director_style'] = styles[(micro_index + offset // 11) % len(styles)]
    x['micro_scene_index'] = micro_index
    x['micro_scene_phase'] = phase
    return x, {'index': micro_index, 'phase': phase, 'interval': interval}


def _micro_scene_transition(im, micro, accent):
    if not micro:
        return im
    phase=float(micro.get('phase') or 0.0)
    interval = max(.1, float(micro.get('interval') or NEWS_MICRO_SCENE_SECONDS))
    if phase >= NEWS_MICRO_TRANSITION_SECONDS / interval:
        return im
    p=ease(phase / (NEWS_MICRO_TRANSITION_SECONDS / interval))
    d=ImageDraw.Draw(im,'RGBA')
    alpha=max(0,int(52*(1-p)))
    idx=int(micro.get('index') or 0)
    if idx % 2:
        d.polygon([(0,0),(int(W*.22*(1-p)),0),(0,H)],fill=accent+(alpha,))
    else:
        d.polygon([(W,0),(W-int(W*.22*(1-p)),H),(W,H)],fill=accent+(alpha,))
    return im


def render_frame(plan,t,genre,total):
    index=next((i for i,s in enumerate(plan) if t<s['end']),len(plan)-1)
    s=plan[index];u=t-s['start']; accent=THEMES[genre][2]
    s,micro=_micro_scene_direction(s,t,genre)
    im=background(genre).copy()
    # Camera treatment is chosen by the director per narrative beat.
    cam=s.get('director_camera','push'); energy=float(s.get('director_energy',.5))
    if cam in {'push','drift','track'}:
        fmt=str(s.get('creative_format') or '')
        motion_boost=1.55 if fmt=='documentary_montage' else 1.0
        scale=1.0 + motion_boost*(0.012+0.018*energy)*ease(min(1,u/max(.4,s['duration'])))
        if cam=='drift':
            scale=1.0 + motion_boost*.010*math.sin(t*.9)
        nw,nh=int(W*scale),int(H*scale)
        moved=im.resize((nw,nh),Image.Resampling.BICUBIC)
        dx=max(0,(nw-W)//2 + (int(math.sin(t*.55)*10*energy) if cam=='track' else 0))
        dy=max(0,(nh-H)//2)
        im=moved.crop((dx,dy,dx+W,dy+H))
    # Exclusively select one primary visual source. Earlier Studio releases
    # drew a handcrafted robot/ship/planet, a director card, collage shapes,
    # an attention widget AND another motion graphic over the same position.
    # That passed numerical creative QA but produced visibly overlapping art.
    from astra_v2.layer_contract import scene_layers
    layers=scene_layers(s)
    if layers['foreground']=='missing_media' and 'resolved_asset' in s:
        # A raw storyboard may be inspected before assets are bound. Actual
        # production scenes must never render blank after failed acquisition.
        raise CreativeReject('Scene media missing from cache: refusing overlapping/filler fallback.')
    if layers['draw_visual']:
        draw_visual(im,s,t,u,accent)
    if str(s.get('creative_format') or '')=='documentary_montage' and .36 < (u/max(.2,s['duration'])) < .62:
        p=(u/max(.2,s['duration'])-.36)/.26
        pulse=1.0+0.018*math.sin(min(1,p)*math.pi)
        nw,nh=int(W*pulse),int(H*pulse)
        moved=im.resize((nw,nh),Image.Resampling.BICUBIC)
        dx=max(0,(nw-W)//2); dy=max(0,(nh-H)//2)
        im=moved.crop((dx,dy,dx+W,dy+H))
    # Transition accents occur under the hero, never on top of the narration
    # captions or newly selected subject illustration.
    transition_layer(im,s,t,u,accent)
    _micro_scene_transition(im,micro,accent)
    if layers['draw_cached_media']:
        im=composite_cached_asset(im,s.get('resolved_asset',{}),t=t,u=u,shot=s)
    elif layers['draw_director_asset']:
        asset_layer(im,s,t,u,accent)
    d=ImageDraw.Draw(im)
    comparison_labels=s.get('comparison_labels') or []
    if len(comparison_labels)==2:
        d.text((250,1220),str(comparison_labels[0]),font=font(24),anchor='mm',fill=(210,218,233))
        d.text((830,1220),str(comparison_labels[1]),font=font(24),anchor='mm',fill=(210,218,233))
    # Director-controlled pattern interrupts are sparse and narrative, not constant.
    if s.get('director_pattern_interrupt') and u<.16:
        a=int(150*(1-u/.16))
        d.line((70,600,940,600),fill=accent+(a,) if im.mode=='RGBA' else accent,width=9)
    # Format-specific identity/headline treatment. Studio 7 deliberately avoids
    # one permanent template surface across every Short.
    fmt=s.get('creative_format','mixed_media_story')
    brand=s.get('format_brand','minimal')
    if brand=='corner':
        d.text((72,108),'RAYVAN',font=font(23),fill=(205,213,228))
    elif brand=='minimal' and index==0 and u<1.1:
        d.text((72,108),'RAYVAN',font=font(21),fill=(205,213,228))
    headline_offset=int((1-ease(u/.24))*18)
    premium_visual=s.get('visual') in {'media','tidal_lock','iss_orbit'}
    show_headline = not premium_visual or u < (.52 if fmt in {'cinematic_mini_doc','microfiction_cinematic'} else .80)
    if show_headline:
        if fmt in {'cinematic_mini_doc','microfiction_cinematic'}:
            box=(72,205+headline_offset,940,330+headline_offset); size=48 if index==0 else 38
        elif fmt=='documentary_montage':
            box=(64,145+headline_offset,955,350+headline_offset); size=74 if index==0 else 50
        elif fmt=='animated_infographic':
            box=(80,150+headline_offset,925,295+headline_offset); size=60 if index==0 else 44
        else:
            box=(72,165+headline_offset,940,318+headline_offset); size=66 if index==0 else 46
        fit_text(d,s['headline'],box,size=size,fill='white',max_lines=2)
    # Phrase captions use actual utterance windows; active word timing is approximate.
    words=s['speech'].split()
    dur=len(s['audio'])/RATE
    pos=max(0,min(len(words)-1,int((t-s['voice_start'])/max(.1,dur)*len(words))))
    mode=s.get('director_caption_mode','phrase')
    width=3 if mode=='keyword' else (4 if mode=='question' else 5)
    chunk=pos//width; text=' '.join(words[chunk*width:(chunk+1)*width])
    if mode=='keyword' and text:
        text=max(text.split(),key=len).upper()
    elif mode=='question' and text and ('?' in s.get('speech','') or s.get('director_role')=='cold_open'):
        text=text.rstrip(' .!?')+'?'
    if s.get('countdown') and t>s['voice_start']+dur+.1: text='YOUR TURN'
    # Caption surface also changes with the selected creative format.
    if fmt in {'cinematic_mini_doc','microfiction_cinematic'}:
        d.rounded_rectangle((118,1530,900,1636),radius=18,fill=(5,8,14))
        fit_text(d,text,(145,1538,874,1628),size=37,fill=(242,245,250),max_lines=2)
    elif fmt=='documentary_montage':
        # Native Shorts-style floating captions: no permanent card/strip.
        # Draw a soft shadow for legibility, then clean white text above it.
        shadow_box=(94,1468,986,1570)
        fit_text(d,text.upper(),(shadow_box[0]+4,shadow_box[1]+5,shadow_box[2]+4,shadow_box[3]+5),
                 size=46,fill=(0,0,0),max_lines=2)
        fit_text(d,text.upper(),shadow_box,size=46,fill='white',max_lines=2)
    elif fmt=='animated_infographic':
        d.rounded_rectangle((170,1450,910,1560),radius=28,fill=(8,12,23))
        fit_text(d,text,(195,1458,885,1552),size=44,fill=accent,max_lines=2)
    else:
        d.rounded_rectangle((126,1470,880,1578),radius=20,fill=(8,12,23))
        fit_text(d,text,(150,1478,856,1568),size=42,fill=(242,245,250),max_lines=2)
    # Brief ink-dark cut transition rather than full-screen flashing.
    if index>0 and u<.13:
        transition=s.get('format_transition','cinematic')
        if transition=='hard-cut':
            pass
        elif transition in {'wipe','snap'}:
            shade=Image.new('RGB',im.size,(8,12,23)); im=Image.blend(shade,im,.30+.70*u/.13)
        else:
            shade=Image.new('RGB',im.size,(8,12,23)); im=Image.blend(shade,im,.55+.45*u/.13)
    return im




def asset_manifest(ch, plan):
    """Create a provenance-aware acquisition/generation brief for every shot."""
    topic=' '.join(str(ch.get('topic') or ch.get('title') or '').split())
    source=str(ch.get('source') or ch.get('news_url') or '').strip()
    secondary=str(ch.get('secondary_source') or '').strip()
    keywords=[str(x).strip().lower() for x in (ch.get('keywords') or []) if str(x).strip()]
    primary=(keywords[0] if keywords else '')
    aliases=[primary] if primary else []
    if primary=='iss':
        aliases.append('international space station')
    manifest=[]
    for i,p in enumerate(plan):
        kind=p.get('director_asset','kinetic-type')
        semantics=p.get('director_semantics',[])
        # This manifest deliberately does not download arbitrary web media.
        # It tells a future provider exactly what is needed and preserves provenance.
        explicit_query=' '.join(str(p.get('media_query') or '').split())
        if explicit_query:
            # Only an editorial beat that deliberately names the needed subject
            # may search an external provider. This preserves semantic isolation.
            strategy='external-verified'
            query=explicit_query
        elif kind=='source-document' and source:
            strategy='source-derived'
            query='Evidence from the cited source for: '+topic
        elif kind in {'map-explainer','mechanism-diagram','comparison-graphic','time-visualization'}:
            strategy='original-procedural'
            query=explicit_query or f'{kind} explaining {topic}'
        elif kind=='editorial-illustration':
            strategy='original-illustration'
            query=explicit_query or ('Non-likeness editorial concept illustrating: '+topic)
        elif kind=='character-scene':
            strategy='character-video-required'
            query=explicit_query or ('Character-driven cinematic scene for: '+topic)
        else:
            strategy='original-motion'
            query=explicit_query or ('Abstract visual metaphor for: '+topic)
        manifest.append({
            'shot':i+1,'kind':kind,'strategy':strategy,'query':query[:240],
            'source_url':source if strategy=='source-derived' else '',
            'secondary_source_url':secondary if strategy=='source-derived' else '',
            'semantics':semantics,
            'required_subject_terms':aliases if strategy=='external-verified' else [],
            'exact_commons_title':str(p.get('media_file') or '').strip() if strategy=='external-verified' else '',
            'media_fit':str(p.get('media_fit') or 'cover') if strategy=='external-verified' else 'cover',
            'media_motion':str(p.get('media_motion') or 'still') if strategy=='external-verified' else 'still',
            'rights_rule':'original-or-explicitly-authorized-only',
            'no_fake_screenshot':True,
            'no_unverified_real_person_likeness':True,
        })
    return manifest


def resolve_assets(manifest):
    """Resolve only safe zero-cost local/original providers; fail to procedural art, never scrape."""
    resolved=[]
    for item in manifest:
        r=dict(item); strategy=item['strategy']
        if strategy in {'original-procedural','original-motion','original-illustration'}:
            r.update(provider='astra-studio',status='ready',cost=0,
                     license='original-generated-by-astra')
        elif strategy=='external-verified':
            # Keep a safe local fallback while the explicit provider request is
            # attempted. Premium stories later require verified subject media.
            r.update(provider='astra-studio',status='ready',cost=0,
                     license='original-generated-by-astra')
        elif strategy=='character-video-required':
            r.update(provider='character-video-engine',status='blocked',cost=0,
                     license='generation-provider-required')
        elif strategy=='source-derived':
            # Source URLs are evidence/provenance, not automatic media licenses.
            # Until an explicitly authorized media provider is configured, render
            # a truthful evidence abstraction rather than copying the webpage.
            r.update(provider='astra-evidence-abstraction',status='ready',cost=0,
                     license='original-abstraction-no-source-media-copied')
        else:
            r.update(provider='none',status='blocked',cost=0,license='unknown')
        # Store the exact contract an external provider must satisfy. This keeps
        # the renderer provider-ready while preserving the zero-cost local fallback.
        r['external_request']=external_media_request(item)
        resolved.append(r)
    return resolved


def external_media_request(item):
    """Describe a rights-safe external-media request without scraping or trusting search-result licenses."""
    q=item.get('query','')
    # Provider contract: adapters may only return media when they can also return
    # a machine-verifiable license/provenance record. Otherwise Astra must ignore it.
    return {
        'query':q,'media_types':['image','video'],
        'allowed_licenses':['cc0','public-domain','authorized-reuse'],
        'require_creator':True,'require_source_url':True,'require_license_url':True,
        'commercial_use_required':True,'modification_required':True,
        'disallow_editorial_only':True,'disallow_unknown_license':True,
    }

def external_media_candidate(item, candidate=None):
    """Validate a future provider result. No candidate means safe local fallback."""
    if not candidate: return None
    license_id=str(candidate.get('license','')).lower()
    required=('asset_url','source_url','license_url','creator')
    if any(not candidate.get(k) for k in required): return None
    if license_id not in {'cc0','public-domain','authorized-reuse'}: return None
    if not candidate.get('commercial_use',False): return None
    if not candidate.get('modification_allowed',False): return None
    out=dict(item)
    out.update(provider=candidate.get('provider','external-authorized'),
               status='ready',cost=float(candidate.get('cost',0)),
               license=license_id,asset_url=candidate['asset_url'],
               commons_title=candidate.get('commons_title',''),
               verified_subject=candidate.get('verified_subject',''),
               provenance={'source_url':candidate['source_url'],
                           'license_url':candidate['license_url'],
                           'creator':candidate['creator']})
    return out


def media_cache_key(item):
    raw=json.dumps({'q':item.get('query',''),'kind':item.get('kind','')},sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def prepare_media_cache(resolved, cache_dir='asset_cache'):
    """Prepare deterministic cache slots; external bytes enter only after provider validation."""
    os.makedirs(cache_dir,exist_ok=True)
    out=[]
    for item in resolved:
        r=dict(item); key=media_cache_key(item)
        r['cache_key']=key
        # Existing local/generated provider remains immediately renderable.
        # A verified external adapter can later place an image at this exact path.
        r['cache_image']=os.path.join(cache_dir,key+'.png')
        r['cache_meta']=os.path.join(cache_dir,key+'.json')
        out.append(r)
    return out

def composite_cached_asset(im,item,t=0.0,u=0.0,shot=None):
    """Composite only a previously validated cached image; malformed assets fail safely."""
    path=item.get('cache_image','')
    if not path or not os.path.isfile(path): return im
    try:
        media=Image.open(path).convert('RGB')
        # Premium media occupies most of the vertical canvas. Diagrams and full
        # celestial discs use contain-fit so important information is never cropped.
        mode=str(item.get('media_fit') or 'cover')
        fmt=str((shot or {}).get('creative_format') or '')
        if fmt=='documentary_montage':
            # Premium documentary shots should feel footage-first, not card-first.
            # Push media nearly edge-to-edge while preserving a compact lower caption band.
            box=(0,165,1080,1505) if mode=='wide' else (0,125,1080,1515)
        else:
            box=(24,540,1056,1180) if mode=='wide' else (40,350,1040,1370)
        bw,bh=box[2]-box[0],box[3]-box[1]
        if mode in {'contain','wide'}:
            scale=min(bw/media.width,bh/media.height)
            nw,nh=max(1,int(media.width*scale)),max(1,int(media.height*scale))
            media=media.resize((nw,nh),Image.Resampling.LANCZOS)
            stage=Image.new('RGB',(bw,bh),(5,8,14))
            stage.paste(media,((bw-nw)//2,(bh-nh)//2))
            media=stage
        else:
            scale=max(bw/media.width,bh/media.height)
            nw,nh=max(1,int(media.width*scale)),max(1,int(media.height*scale))
            media=media.resize((nw,nh),Image.Resampling.LANCZOS)
            x=max(0,(nw-bw)//2); y=max(0,(nh-bh)//2)
            media=media.crop((x,y,x+bw,y+bh))
        motion=str(item.get('media_motion') or ((shot or {}).get('media_motion') if shot else '') or 'still')
        if motion=='push':
            progress=min(1.0,max(0.0,u/max(.2,float((shot or {}).get('duration') or 3.0))))
            zoom_strength=.060 if str((shot or {}).get('creative_format') or '')=='documentary_montage' else .035
            zoom=1.0+zoom_strength*progress
            zw,zh=int(bw*zoom),int(bh*zoom)
            moved=media.resize((zw,zh),Image.Resampling.BICUBIC)
            x=max(0,(zw-bw)//2); y=max(0,(zh-bh)//2)
            media=moved.crop((x,y,x+bw,y+bh))
        im.paste(media,(box[0],box[1]))
    except Exception:
        return im
    return im


def ingest_authorized_media(item, candidate, cache_dir='asset_cache'):
    """Validate, download and cache an explicitly reusable image from a provider adapter."""
    checked=external_media_candidate(item,candidate)
    if not checked: return None
    if float(checked.get('cost',0))!=0: return None
    url=checked.get('asset_url','')
    if not url.startswith('https://'): return None
    key=media_cache_key(item); os.makedirs(cache_dir,exist_ok=True)
    image_path=os.path.join(cache_dir,key+'.png')
    meta_path=os.path.join(cache_dir,key+'.json')
    try:
        import urllib.request, io
        req=urllib.request.Request(url,headers={'User-Agent':'RAYVAN-Astra/1.0'})
        with urllib.request.urlopen(req,timeout=12) as resp:
            ctype=str(resp.headers.get('Content-Type','')).lower()
            length=int(resp.headers.get('Content-Length') or 0)
            if 'image/' not in ctype or length>12_000_000: return None
            raw=resp.read(12_000_001)
        if len(raw)>12_000_000: return None
        img=Image.open(io.BytesIO(raw)); img.verify()
        img=Image.open(io.BytesIO(raw)).convert('RGB')
        if img.width<480 or img.height<480: return None
        img.save(image_path,'PNG',optimize=True)
        checked.update(cache_key=key,cache_image=image_path,cache_meta=meta_path)
        with open(meta_path,'w',encoding='utf-8') as h:
            json.dump({k:v for k,v in checked.items() if k!='external_request'},h,indent=2)
        return checked
    except Exception:
        return None

def provider_adapter(item):
    """Zero-cost Wikimedia Commons adapter with strict subject and rights checks."""
    try:
        import urllib.parse, urllib.request, re, html
        raw_q=' '.join(str(item.get('query','')).split())[:180]
        required=[str(x).strip().lower() for x in item.get('required_subject_terms',[]) if str(x).strip()]
        if not raw_q or not required: return None
        # Rights boilerplate made Commons search drift toward unrelated NASA PDFs.
        # Search the editorial subject, then verify the returned file title itself.
        q=re.sub(r'(?i)\b(public domain|nasa|diagram|full disk|full planet|image|photo)\b',' ',raw_q)
        q=' '.join(q.split())[:160] or raw_q
        api='https://commons.wikimedia.org/w/api.php'
        exact=str(item.get('exact_commons_title') or '').strip()
        if exact:
            params={'action':'query','titles':exact,'prop':'imageinfo','iiprop':'url|extmetadata',
                    'iiurlwidth':'1800','format':'json','origin':'*'}
        else:
            params={'action':'query','generator':'search','gsrsearch':q,'gsrnamespace':'6',
                    'gsrlimit':'20','prop':'imageinfo','iiprop':'url|extmetadata',
                    'iiurlwidth':'1400','format':'json','origin':'*'}
        url=api+'?'+urllib.parse.urlencode(params)
        req=urllib.request.Request(url,headers={'User-Agent':'RAYVAN-Astra/1.0 (automated media research)'})
        with urllib.request.urlopen(req,timeout=12) as resp:
            data=json.loads(resp.read(2_000_000).decode('utf-8'))
        pages=(data.get('query') or {}).get('pages') or {}
        for page in pages.values():
            infos=page.get('imageinfo') or []
            if not infos: continue
            title=str(page.get('title') or '').strip()
            low_title=title.lower()
            # Document cover thumbnails are not story footage.
            if low_title.endswith(('.pdf','.djvu','.tif','.tiff')): continue
            info=infos[0]; meta=info.get('extmetadata') or {}
            def mv(k):
                v=(meta.get(k) or {}).get('value','')
                return html.unescape(re.sub('<[^>]+>',' ',str(v))).strip()
            object_name=mv('ObjectName')
            subject_text=(title+' '+object_name).lower()
            subject_tokens=set(re.findall(r'[a-z0-9]+',subject_text))
            if exact:
                # Exact files are editorially pinned and fetched by exact Commons
                # page title; their identity is stronger than fuzzy search tokens.
                if title.strip().lower() != exact.strip().lower():
                    continue
            else:
                def term_match(term):
                    # Exact token matching prevents Earth's "Moon" from matching
                    # unrelated titles that merely contain "moons".
                    words=[w for w in re.findall(r'[a-z0-9]+',term) if w]
                    return bool(words) and all(w in subject_tokens for w in words)
                if not any(term_match(term) for term in required):
                    continue
                if any(bad in subject_tokens for bad in {'fictional','extrasolar','exoplanet'}):
                    continue
            license_short=mv('LicenseShortName').lower()
            usage=mv('UsageTerms').lower()
            restrictions=mv('Restrictions').lower()
            artist=mv('Artist') or info.get('user') or 'Wikimedia Commons contributor'
            license_url=mv('LicenseUrl')
            source_page=info.get('descriptionurl') or info.get('descriptionshorturl')
            asset_url=info.get('thumburl') or info.get('url')
            pd=(license_short in {'public domain','public domain mark','pdm','cc0','cc zero'} or
                'public domain' in usage or 'cc0' in usage)
            if not pd or restrictions or not all((asset_url,source_page,artist)): continue
            if not license_url:
                license_url='https://creativecommons.org/publicdomain/mark/1.0/'
            return {'provider':'wikimedia-commons','asset_url':asset_url,
                    'source_url':source_page,'license_url':license_url,'creator':artist,
                    'license':'public-domain','commercial_use':True,
                    'modification_allowed':True,'cost':0,
                    'verified_subject':required[0],'commons_title':title}
    except Exception:
        return None
    return None

def acquire_story_media(resolved):
    """Acquire external media only when a shot explicitly requests it.

    Studio 5 accidentally searched Wikimedia even for procedural/illustration
    shots, so a keyword-near but semantically unrelated public-domain image
    could cover a purpose-built visual. Studio 6 keeps local art local.
    """
    out=[]
    for item in resolved:
        if item.get('strategy') != 'external-verified':
            out.append(item)
            continue
        candidate=provider_adapter(item)
        print('Premium media resolve:', json.dumps({
            'query': item.get('query',''),
            'required_subject_terms': item.get('required_subject_terms',[]),
            'candidate_title': (candidate or {}).get('commons_title'),
            'resolved': bool(candidate),
        }, ensure_ascii=False))
        acquired=ingest_authorized_media(item,candidate) if candidate else None
        out.append(acquired or item)
    return out

def asset_resolution_gate(resolved):
    blocked=[x for x in resolved if x.get('status')!='ready']
    unsafe=[x for x in resolved if not str(x.get('license','')).startswith(('original-','cc0','public-domain','authorized-'))]
    if blocked or unsafe:
        raise CreativeReject('Asset gate rejected unresolved/unsafe media: '+json.dumps({'blocked':blocked,'unsafe':unsafe}))
    return {'ready':len(resolved),'providers':sorted({x['provider'] for x in resolved}),
            'zero_cost':all(float(x.get('cost',0))==0 for x in resolved)}

def creative_quality_gate(ch, plan):
    """Fail closed when a rendered story would still behave like a generic template."""
    if not plan: raise CreativeReject('Creative gate: empty shot plan.')
    assets=[p.get('director_asset','') for p in plan]
    roles=[p.get('director_role','') for p in plan]
    motions=[p.get('director_motion','') for p in plan]
    semantics={x for p in plan for x in p.get('director_semantics',[])}
    score=35
    score+=min(20,len(set(assets))*6)
    score+=min(12,len(set(motions))*4)
    score+=min(12,len(set(roles))*3)
    score+=min(10,len(semantics)*3)
    if assets and assets[0] != 'kinetic-type': score+=5
    if any(a in {'source-document','map-explainer','mechanism-diagram','comparison-graphic','time-visualization'} for a in assets): score+=8
    if ch.get('genre')=='current':
        if int(ch.get('source_count') or 0)>0 and 'source-document' not in assets: score-=12
        if len(set(assets))<2: score-=20
        if not semantics: score-=18
    generic_ratio=(sum(a=='kinetic-type' for a in assets)/max(1,len(assets)))
    if generic_ratio>.60: score-=18
    styles=[p.get('director_style','') for p in plan]
    layouts=[p.get('director_layout','center') for p in plan]
    beats=[p.get('story_beat','') for p in plan if p.get('story_beat')!='cta']
    if ch.get('genre')=='current':
        if len(set(beats))>=4: score+=7
        if len(beats)>=4 and len(set(beats))<3: score-=18
        if int(ch.get('source_count') or 0)>0 and not any(str(b).startswith('evidence') for b in beats): score-=15
    adjacent_repeats=sum(1 for a,b in zip(styles,styles[1:]) if a and a==b)
    layout_repeats=sum(1 for a,b in zip(layouts,layouts[1:]) if a==b)
    if len(set(styles))>=3: score+=8
    elif len(set(styles))<2 and len(styles)>=3: score-=18
    if adjacent_repeats>1: score-=min(18,adjacent_repeats*6)
    if len(set(layouts))>=3: score+=6
    elif len(set(layouts))<2 and len(layouts)>=3: score-=14
    if layout_repeats>1: score-=min(12,layout_repeats*4)
    # A high numeric diversity score must not pass a semantically absurd plan.
    topic_low=' '.join(str(ch.get(k) or '') for k in ('topic','question','answer','news_title')).lower()
    sports=bool(re.search(r'cricket|football|soccer|tennis|batter|bowler|innings|match|player|samson',topic_low))
    space=bool(re.search(r'planet|moon|orbit|eclipse|space|jupiter|venus|mars|nasa',topic_low))
    if sports and any(a in {'map-explainer','mechanism-diagram'} for a in assets):
        score-=22
    if sports and 'source-document' not in assets:
        score-=18
    if space and 'map-explainer' in assets:
        score-=12
    # Repetition that looks like a template is a hard creative smell.
    if adjacent_repeats>=3: score-=24
    # Cold open must have a deliberate visual language, not an empty/default frame.
    if styles and styles[0] in {'cel-shaded','stylized-cgi','mixed-media'}: score+=5
    # Hard semantic/editorial failures cannot be hidden by a high diversity score.
    hard_failures=[]
    if ch.get('genre')=='current':
        subject=(str(ch.get('topic') or '') or str(ch.get('hook') or '')).strip().lower()
        headline=str(ch.get('news_title') or '').strip().lower()
        # The selected trend subject must actually be represented in the cited story angle.
        subject_tokens=[t for t in re.findall(r'[a-z0-9]+',subject) if len(t)>2]
        if subject_tokens and headline and not any(t in headline for t in subject_tokens):
            hard_failures.append('trend subject is not supported by the selected headline')
        if int(ch.get('source_count') or 0)>0 and 'source-document' not in assets:
            hard_failures.append('current story has no source-evidence shot')
        # A repaired plan made only from abstractions is not automatically premium footage.
        original_illustrations=sum(a=='editorial-illustration' for a in assets)
        source_docs=sum(a=='source-document' for a in assets)
        if len(assets)>=5 and original_illustrations+source_docs >= len(assets)-1:
            hard_failures.append('visual plan is dominated by repeated illustration/document abstractions')
    score=max(0,min(100,score))
    if hard_failures:
        score=min(score,55)
    report={'score':score,'assets':assets,'roles':roles,'motions':motions,
            'semantics':sorted(semantics),'generic_ratio':round(generic_ratio,2),
            'styles':styles,'adjacent_style_repeats':adjacent_repeats,
            'layouts':layouts,'adjacent_layout_repeats':layout_repeats,
            'hard_failures':hard_failures}
    if score<78:
        raise CreativeReject('Creative gate rejected generic/weak visual plan: '+json.dumps(report))
    return report

def _repair_plan(ch,plan,attempt):
    """Deterministically rebuild weak visual direction without weakening the gate."""
    repaired=[]
    assets=['editorial-illustration','map-explainer','mechanism-diagram','comparison-graphic','source-document']
    styles=['stylized-cgi','vector-motion','mixed-media','cel-shaded','stop-motion']
    layouts=['focus-left','focus-right','center','split']
    for i,raw in enumerate(plan):
        x=dict(raw)
        if x.get('story_beat')=='cta':
            repaired.append(x); continue
        beat=x.get('story_beat','')
        topic_low=' '.join(str(ch.get(k) or '') for k in ('topic','question','answer','news_title')).lower()
        sports=bool(re.search(r'cricket|football|soccer|tennis|batter|bowler|innings|match|player|samson',topic_low))
        preferred={'map':'map-explainer','mechanism':'mechanism-diagram','contrast':'comparison-graphic',
                   'evidence':'source-document','uncertainty':'source-document',
                   'reveal':'editorial-illustration','consequence':'editorial-illustration',
                   'payoff':'editorial-illustration'}.get(beat,assets[(i+attempt)%len(assets)])
        if sports and preferred in {'map-explainer','mechanism-diagram'}:
            preferred='editorial-illustration' if beat!='evidence' else 'source-document'
        x['director_asset']=preferred
        x['director_style']=styles[(i+attempt)%len(styles)]
        x['director_layout']=layouts[(i+attempt)%len(layouts)]
        x['director_motion']=['arc','scan','pulse','parallax'][(i+attempt)%4]
        repaired.append(x)
    return repaired

def render_short(ch,out,still_dir=None,director_repair_pass=0,scene_surgery=None):
    genre=ch.get('genre','challenge')
    if genre not in THEMES: raise ValueError('Unsupported genre')
    plan=make_plan(ch)
    if int(director_repair_pass or 0) > 0:
        plan=_repair_plan(ch,plan,int(director_repair_pass))
    if scene_surgery:
        from retention_surgery import apply_surgery
        plan=apply_surgery(plan, scene_surgery)
    # Repair/re-score weak plans before abandoning a publish slot.
    repair_attempts=0
    while True:
        try:
            creative_quality_gate(ch,plan); break
        except RuntimeError:
            if repair_attempts>=2: raise
            repair_attempts+=1
            plan=_repair_plan(ch,plan,repair_attempts)
    if any(s.get("creative_format")=="ai_character_cinematic" for s in plan):
        ch["character_storyboard_plan"]=character_storyboard(ch,plan)
    assets=asset_manifest(ch,plan)
    resolved_assets=prepare_media_cache(resolve_assets(assets))
    resolved_assets=acquire_story_media(resolved_assets)
    asset_report=asset_resolution_gate(resolved_assets)
    if ch.get('premium_story'):
        verified=sum(1 for x in resolved_assets if x.get('provider')=='wikimedia-commons')
        required=sum(1 for x in resolved_assets if x.get('strategy')=='external-verified')
        if not required or verified != required:
            raise CreativeReject(
                f'Creative gate rejected premium story: verified subject media {verified}/{required}; all editorial shots must resolve.'
            )
        asset_report['verified_subject_media']=verified
        asset_report['required_subject_media']=required
    # Bind resolved asset metadata to the corresponding directed shot.
    for shot,item in zip(plan,resolved_assets): shot['resolved_asset']=item
    creative_report=creative_quality_gate(ch,plan)
    creative_report['repair_attempts']=repair_attempts
    creative_report['asset_manifest']=resolved_assets
    creative_report['asset_resolution']=asset_report
    from astra_v2.layer_contract import verify_scene_layout
    layer_report=verify_scene_layout(plan)
    if not layer_report['pass']:
        raise CreativeReject('Scene collision QA failed: '+json.dumps(layer_report['failures']))
    duration=voice_plan(plan,genre,max_duration=min(59.0,float(ch.get('target_duration_max',59))),
                        voice_name=str(ch.get('voice_profile') or 'af_heart'),
                        voice_speed=float(ch.get('voice_speed') or 1.09))
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='astra_studio_') as tmp:
        tmp=Path(tmp);audio=tmp/'mix.wav'
        audio_info=score_audio(plan,duration,genre,audio)
        count=math.ceil(duration*FPS);actual_duration=count/FPS
        cmd=[get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0',
             '-i',str(audio),'-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','18',
             '-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
             '-af','loudnorm=I=-14:TP=-1.0:LRA=7','-movflags','+faststart','-shortest',str(out)]
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
    micro_count=(math.ceil(actual_duration / NEWS_MICRO_SCENE_SECONDS) if genre=='current' else len(plan))
    visual_rate=(micro_count / actual_duration) if actual_duration > 0 else 0.0
    report={'renderer':VERSION,'genre':genre,'frames':count,'duration':round(actual_duration,3),
            'resolution':[W,H],'fps':FPS,'audio':audio_info,'creative_quality':creative_report,'layer_qa':layer_report,
            'visual_edit':{
                'narration_beat_count':len(plan),
                'visual_scene_count':micro_count,
                'visual_scene_rate_per_second':round(visual_rate,3),
                'target_scene_rate_range':[1.0,2.0] if genre=='current' else None,
                'micro_scene_seconds':NEWS_MICRO_SCENE_SECONDS if genre=='current' else None,
                'transition_seconds':NEWS_MICRO_TRANSITION_SECONDS if genre=='current' else None,
            },
            'scenes':[{k:v for k,v in s.items() if k!='audio'} for s in plan]}
    print('Studio render:',json.dumps({k:v for k,v in report.items() if k!='scenes'}))
    return report


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Render a Studio preview without authentication or uploads.')
    parser.add_argument('--preview',type=Path)
    parser.add_argument('--premium-preview',type=Path)
    parser.add_argument('--stills-dir',type=Path)
    args=parser.parse_args()
    if args.premium_preview:
        from premium_stories import catalog as premium_catalog
        demo=premium_catalog()[0]
        report=render_short(demo,args.premium_preview,still_dir=args.stills_dir)
        report_path=args.premium_preview.with_suffix('.json')
        report_path.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    elif args.preview:
        demo=dict(genre='space',content_id='venus-spin',hook='ONE SPIN',
                  question='Venus rotates slowly.',answer='243 Earth days per rotation.')
        render_short(demo,args.preview)
    else:
        parser.error('one of --preview or --premium-preview is required')
