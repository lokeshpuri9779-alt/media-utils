"""Original landscape explainers. Each episode has an explicit researched script.

Weekly capacity is a cap, not an excuse to republish the same episode. Exhausted
catalogs stop long-form publication until a new sourced episode is added.
"""
from datetime import datetime, timedelta
from pathlib import Path
import json, math, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import studio_renderer as studio

EPISODE_ID='planet-clocks-v1'
TITLE='Why a Day Can Be Longer Than a Year | Venus and Mercury Explained'
SOURCES=[
    'https://science.nasa.gov/earth/facts/',
    'https://science.nasa.gov/venus/venus-facts/',
    'https://nssdc.gsfc.nasa.gov/planetary/factsheet/venusfact.html',
    'https://science.nasa.gov/mercury/facts/',
]


def long_plan():
    # Original narration, with rounded planetary periods grounded in NASA sources.
    rows=[
      ('A DAY LONGER THAN A YEAR?','Imagine celebrating a new year before your planet has finished turning around once. On Venus, that is possible. But there is a catch hidden inside the word day.', 'VENUS','planet','01 / THREE DIFFERENT CLOCKS'),
      ('WHAT DOES DAY MEAN?','A rotation, a sunrise, and a trip around the Sun are three different clocks. On Earth they feel familiar. On our neighbours, they produce some wonderfully strange results.','THREE CLOCKS','clocks','01 / THREE DIFFERENT CLOCKS'),
      ('CLOCK ONE: ROTATION','First, imagine a distant star as a reference point. Time how long your planet takes to face the same direction again. That gives you its rotation period.','ONE SPIN','planet','01 / THREE DIFFERENT CLOCKS'),
      ('CLOCK TWO: SOLAR DAY','Now use the Sun as your reference instead. A solar day tracks its return to the same position in the sky. Rotation and travel around the Sun both affect that clock.','SUN TO SUN','orbit','01 / THREE DIFFERENT CLOCKS'),
      ('CLOCK THREE: THE YEAR','Finally, count one complete journey around the Sun. That is a year. These clocks describe different motions, so there is no rule saying a rotation must finish first.','ONE ORBIT','orbit','01 / THREE DIFFERENT CLOCKS'),
      ('START WITH EARTH','Earth makes one rotation in roughly twenty-three hours and fifty-six minutes. Our familiar mean solar day is twenty-four hours. Those numbers are close, but they are not identical.','23 h 56 min','planet','02 / EARTH: THE FAMILIAR CLOCK'),
      ('WHY THE EXTRA MINUTES?','While Earth turns, it also moves along its orbit. After one spin relative to distant stars, it needs a little more rotation to bring the Sun back to the same direction.','TWO MOTIONS','orbit','02 / EARTH: THE FAMILIAR CLOCK'),
      ('A YEAR IS NOT 365 EXACTLY','Earth takes about three hundred sixty-five and a quarter days to orbit the Sun. That mismatch is why calendars need adjustments. Our everyday timekeeping is already an approximation.','365.25 DAYS','timeline','02 / EARTH: THE FAMILIAR CLOCK'),
      ('VENUS CHANGES THE RULES','Now move to Venus. One rotation takes about two hundred forty-three Earth days. Its orbit takes only about two hundred twenty-five. The orbital clock reaches the finish line first.','243 > 225','timeline','03 / VENUS: THE SLOW SPINNER'),
      ('THE YEAR FINISHES FIRST','Picture two progress bars starting together. The year bar reaches one hundred percent while the rotation bar is still moving. That is the precise surprise behind the famous Venus fact.','ROTATION / ORBIT','timeline','03 / VENUS: THE SLOW SPINNER'),
      ('IT ALSO SPINS BACKWARD','There is another complication. Venus rotates in the opposite direction to Earth. Astronomers call that retrograde rotation. The direction matters when you combine rotation with movement around the Sun.','RETROGRADE','planet','03 / VENUS: THE SLOW SPINNER'),
      ('243 IS NOT THE SOLAR DAY','The two hundred forty-three day figure describes a rotation relative to the stars. Venus has a solar day of roughly one hundred seventeen Earth days. These are different measurements.','117 EARTH DAYS','clocks','03 / VENUS: THE SLOW SPINNER'),
      ('ASK WHICH CLOCK','So when somebody says a day on Venus is longer than a year, ask which kind of day they mean. The statement works for its rotation period, not its solar day.','DEFINE THE DAY','clocks','03 / VENUS: THE SLOW SPINNER'),
      ('MERCURY HAS ANOTHER TWIST','Mercury offers a different surprise. Its year lasts about eighty-eight Earth days, and it rotates once in roughly fifty-nine. So a single rotation is shorter than its year.','59 / 88','planet','04 / MERCURY: TWO YEARS IN A DAY'),
      ('BUT WAIT FOR THE SUN','Yet one full solar day on Mercury takes about one hundred seventy-six Earth days. That is about two Mercury years between equivalent positions of the Sun in its sky.','176 EARTH DAYS','orbit','04 / MERCURY: TWO YEARS IN A DAY'),
      ('THREE SPINS, TWO ORBITS','Mercury completes about three rotations for every two orbits. That relationship is called a three-to-two spin-orbit resonance. The clocks are linked, but they still measure different things.','3 SPINS : 2 ORBITS','clocks','04 / MERCURY: TWO YEARS IN A DAY'),
      ('THE SIMPLE COMPARISON','On Venus, a rotation outlasts a year. On Mercury, a solar day outlasts a year. Similar sounding headlines can describe different physical relationships. The definition changes the answer.','SAME WORD. DIFFERENT CLOCK.','timeline','05 / THE TAKEAWAY'),
      ('TRY THE TWO-CLOCK TEST','The next time you see a surprising planetary time fact, look for two labels. What motion is being timed? And are the units Earth hours, Earth days, or that planet\'s own days?','MOTION + UNITS','clocks','05 / THE TAKEAWAY'),
      ('YOUR TURN','Which surprised you more: Venus finishing a year before one spin, or Mercury taking two years for a solar day? Tell us in the comments. The source links are below.','VENUS OR MERCURY?','planet','05 / THE TAKEAWAY'),
      ('KEEP EXPLORING','If this helped, like the video or share it with someone who enjoys space. Subscribe to Loki the Game Changer for more clear visual explainers. There is always another clock to question.','SUBSCRIBE FOR MORE','orbit','05 / THE TAKEAWAY'),
    ]
    plan=[]
    for h,s,label,visual,chapter in rows:
        scene=studio.scene(h,s,visual,label,'',duration=0)
        scene.update(chapter=chapter,planet='earth' if chapter.startswith('02') else 'mercury' if chapter.startswith('04') else 'venus')
        plan.append(scene)
    return plan


def choose_episode(data,now):
    """One new long episode at most per rolling seven days, after 19:00 IST.

    Publish the sourced Planet Clocks episode first. After that, generate a fresh
    procedural Brain Arena episode every eligible ISO week so long-form never
    runs out of original material.
    """
    if now.hour<19:return None
    planet_published=False
    seen_ids=set()
    for entry in data.get('videos',{}).values():
        cid=entry.get('content_id')
        if cid:seen_ids.add(cid)
        if cid==EPISODE_ID:planet_published=True
        if entry.get('format')=='long':
            try:
                if now-datetime.fromisoformat(entry['published_at'])<timedelta(days=7):return None
            except (KeyError,ValueError,TypeError):continue
    if not planet_published:
        return EPISODE_ID
    iso=now.isocalendar()
    weekly_id=f"brain-arena-{iso.year}-W{iso.week:02d}"
    return None if weekly_id in seen_ids else weekly_id


@studio.lru_cache(maxsize=1)
def wide_background():
    y,x=np.mgrid[0:1080,0:1920]
    g=np.exp(-((x-800)**2/1100**2+(y-460)**2/680**2))
    arr=np.stack([8+g*10,11+g*13,28+g*24],axis=2).astype(np.uint8)
    im=Image.fromarray(arr);d=ImageDraw.Draw(im);rng=np.random.default_rng(11)
    for _ in range(100):
        px,py=int(rng.integers(0,1920)),int(rng.integers(0,1080));v=int(rng.integers(25,70))
        d.ellipse((px,py,px+2,py+2),fill=(v,v,v+15))
    return im


@studio.lru_cache(maxsize=1)
def mercury_texture():
    tex=studio.planet_texture().convert('LA').convert('RGBA')
    d=ImageDraw.Draw(tex);rng=np.random.default_rng(88)
    for _ in range(65):
        x,y=int(rng.integers(100,500)),int(rng.integers(100,500));r=int(rng.integers(5,23))
        if (x-300)**2+(y-300)**2<245**2:
            d.ellipse((x-r,y-r,x+r,y+r),outline=(64,65,69,160),width=3)
    return tex


def frame(plan,t,total):
    index=next((i for i,s in enumerate(plan) if t<s['end']),len(plan)-1)
    s=plan[index];u=t-s['start'];accent=(255,184,105)
    im=wide_background().copy();d=ImageDraw.Draw(im)
    d.rounded_rectangle((60,48,112,100),radius=15,fill=accent)
    d.text((86,73),'L',font=studio.font(35),fill=(10,15,27),anchor='mm')
    d.text((135,62),'LOKI / EXPLAINED',font=studio.font(26),fill=(211,219,239))
    d.text((1860,77),s['chapter'],font=studio.font(24),fill=accent,anchor='rm')
    # Narrative text and captions occupy the right column; illustration is left.
    studio.fit_text(d,s['headline'],(1020,190,1830,458),size=77,max_lines=3)
    studio.fit_text(d,s['label'],(1050,492,1810,620),size=55,fill=accent,max_lines=2)
    cx,cy=505,515
    if s['visual']=='planet':
        tex=mercury_texture() if s['planet']=='mercury' else studio.planet_texture(s['planet']=='earth')
        size=int(510+18*math.sin(t*.19));tex=tex.resize((size,size),Image.Resampling.LANCZOS)
        im.paste(tex,(int(cx-size/2),int(cy-size/2)),tex)
        d=ImageDraw.Draw(im)
        direction=-1 if s['planet']=='venus' else 1
        angle=int(t*direction*16)
        d.arc((180,385,840,645),angle,angle+90,fill=accent,width=4)
    elif s['visual']=='orbit':
        d.ellipse((110,315,900,710),outline=(79,91,129),width=3)
        d.ellipse((455,465,555,565),fill=(255,211,138))
        theta=t*.3;px=cx+395*math.cos(theta);py=512+198*math.sin(theta)
        tex=(mercury_texture() if s['planet']=='mercury' else studio.planet_texture(s['planet']=='earth')).resize((135,135),Image.Resampling.LANCZOS)
        im.paste(tex,(int(px-67),int(py-67)),tex)
    elif s['visual']=='timeline':
        bars=[('VENUS ROTATION',243),('VENUS YEAR',225)]
        if s['planet']=='earth':bars=[('EARTH YEAR',365.25),('CALENDAR YEAR',365)]
        if s['chapter'].startswith('05'):bars=[('VENUS ROTATION',243),('MERCURY SOLAR DAY',176)]
        scale=max(v for _,v in bars)
        for k,(label,val) in enumerate(bars):
            y=405+k*200;d.text((100,y-65),label,font=studio.font(29),fill=(205,213,231))
            d.rounded_rectangle((100,y,910,y+60),radius=20,fill=(35,39,61))
            d.rounded_rectangle((100,y,100+810*val/scale*studio.ease(u/1.2),y+60),radius=20,fill=accent if k==0 else (117,185,255))
            d.text((100,y+88),str(val)+' EARTH DAYS',font=studio.font(24),fill=(155,171,199))
    else:
        for k,label in enumerate(['ROTATION','SOLAR DAY','YEAR']):
            x=240+k*265;r=100
            d.ellipse((x-r,420-r,x+r,420+r),outline=(72,84,117),width=5)
            angle=t*(.5+k*.15)-math.pi/2
            d.line((x,420,x+82*math.cos(angle),420+82*math.sin(angle)),fill=accent,width=5)
            d.ellipse((x-7,413,x+7,427),fill=accent)
            d.text((x,575),label,font=studio.font(25),fill=(180,197,219),anchor='mm')
        d.text((505,735),'DIFFERENT REFERENCE POINTS',font=studio.font(27),fill=(161,179,205),anchor='mm')
    d=ImageDraw.Draw(im)
    words=s['speech'].split();pos=max(0,min(len(words)-1,int((t-s['voice_start'])/max(.1,len(s['audio'])/studio.RATE)*len(words))))
    phrase=' '.join(words[(pos//10)*10:(pos//10+1)*10])
    d.rounded_rectangle((1020,685,1835,875),radius=25,fill=(7,12,26))
    studio.fit_text(d,phrase,(1050,700,1805,860),size=44,fill=(216,228,246),max_lines=3)
    d.text((90,921),'ORIGINAL ANIMATION / ILLUSTRATION, NOT TO SCALE',font=studio.font(20),fill=(123,144,178))
    d.line((60,978,1860,978),fill=(46,58,86),width=4)
    d.line((60,978,60+1800*t/total,978),fill=accent,width=4)
    for s2 in plan:
        x=60+1800*s2['start']/total;d.line((x,973,x,984),fill=(133,147,170),width=2)
    d.text((60,1020),'THE PLANET CLOCKS',font=studio.font(24),fill=(163,184,211))
    d.text((1860,1020),f'{int(t)//60}:{int(t)%60:02d} / {int(total)//60}:{int(total)%60:02d}',font=studio.font(24),fill=(163,184,211),anchor='rm')
    if index and u<.15:im=Image.blend(Image.new('RGB',im.size,(8,11,28)),im,.55+.45*u/.15)
    return im


def chapter_lines(plan):
    out=[];seen=set()
    for s in plan:
        if s['chapter'] in seen:continue
        seen.add(s['chapter']);sec=int(s['start']);out.append(f'{sec//60}:{sec%60:02d} '+s['chapter'].split(' / ',1)[1].title())
    return out


def thumbnail(out):
    im=wide_background().copy();tex=studio.planet_texture().resize((780,780),Image.Resampling.LANCZOS)
    im.paste(tex,(1070,160),tex);d=ImageDraw.Draw(im)
    studio.fit_text(d,'A DAY\nLONGER THAN\nA YEAR?',(90,200,1040,800),size=143,fill=(255,195,116),max_lines=3)
    d.text((100,100),'LOKI / EXPLAINED',font=studio.font(38),fill=(206,223,244))
    d.text((105,925),'THE CLOCK YOU CHOOSE CHANGES THE ANSWER',font=studio.font(29),fill=(182,202,227))
    im.resize((1280,720),Image.Resampling.LANCZOS).save(out,'JPEG',quality=92)


def render(out,still_dir=None,episode_id=EPISODE_ID):
    if episode_id != EPISODE_ID:
        from longform_challenges import render as render_challenges
        return render_challenges(out, episode_id)
    plan=long_plan();total=studio.voice_plan(plan,'space',max_duration=480)
    if total<150:raise RuntimeError('Long episode is too short; add substance rather than padding.')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='astra_long_') as td:
        td=Path(td);audio=td/'mix.wav';audio_info=studio.score_audio(plan,total,'space',audio)
        count=math.ceil(total*studio.FPS)
        cmd=[studio.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(studio.FPS),'-i','pipe:0','-i',str(audio),'-c:v','libx264','-preset','fast','-crf','18','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=9','-shortest','-movflags','+faststart',str(out)]
        with (td/'ffmpeg.log').open('wb') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            try:
                for i in range(count):
                    proc.stdin.write(frame(plan,i/studio.FPS,total).tobytes())
                    if i and i%(studio.FPS*30)==0:print('Long-form rendered seconds:',i//studio.FPS,flush=True)
                proc.stdin.close()
                if proc.wait(timeout=120):raise RuntimeError('Long-form encoding failed')
            except Exception:
                proc.kill();proc.wait();raise
    thumb=out.with_suffix('.jpg');thumbnail(thumb)
    chapters=chapter_lines(plan)
    description='Three planetary clocks: rotation, solar day, and year. An original visual explainer.\n\n'+'\n'.join(chapters)+'\n\nSources:\n'+'\n'.join(SOURCES)+'\n\nWhich surprised you more: Venus or Mercury? Tell us in the comments. Subscribe for more visual explainers.\nOriginal animation and music; AI-assisted script and synthetic narration.\nhttps://www.youtube.com/channel/UCc9fHSuRnqq_C2C0DpLyRRg?sub_confirmation=1'
    if still_dir:
        folder=Path(still_dir);folder.mkdir(parents=True,exist_ok=True)
        for i in (0,5,8,11,13,16):frame(plan,plan[i]['start']+1,total).save(folder/f'chapter_{i}.jpg',quality=93)
    report={'renderer':studio.VERSION,'format':'long','genre':'space','content_id':EPISODE_ID,'duration':round(total,3),'resolution':[1920,1080],'fps':studio.FPS,'scene_count':len(plan),'audio':audio_info,'chapters':chapters,'thumbnail':str(thumb)}
    out.with_suffix('.json').write_text(json.dumps(report,indent=2))
    print('Long-form complete:',json.dumps(report),flush=True)
    return TITLE,description,report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--preview',type=Path,required=True);p.add_argument('--stills',type=Path)
    args=p.parse_args();render(args.preview,args.stills)
