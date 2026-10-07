from __future__ import annotations

import json, math, subprocess, tempfile, time, re
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from premium_stories import catalog
from studio_renderer import (
    make_plan, creative_quality_gate, asset_manifest, resolve_assets,
    prepare_media_cache, acquire_story_media, asset_resolution_gate,
    voice_plan, score_audio, background, draw_visual, THEMES, W, H, FPS
)


def _ass_escape(s: str) -> str:
    return str(s).replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}').replace('\n', r'\N')


def _caption_chunks(text: str):
    """Split narration into readable phrase units without dangling sentence fragments."""
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\\s+', str(text).strip()) if x.strip()]
    out=[]
    for sentence in sentences:
        words=sentence.split()
        if len(words)<=5:
            out.append(' '.join(words))
            continue
        pos=0
        while pos < len(words):
            remaining=len(words)-pos
            take=5 if remaining>=5 else remaining
            if remaining==6:
                take=3
            elif remaining==7:
                take=4
            elif remaining==8:
                take=4
            chunk=words[pos:pos+take]
            pos+=take
            if len(chunk)==1 and out:
                out[-1] += ' ' + chunk[0]
            else:
                out.append(' '.join(chunk))
    return out


def _write_ass(plan, path: Path):
    # Minimal native-Shorts captions: floating white text with outline, no card.
    lines = [
        '[Script Info]',
        'ScriptType: v4.00+',
        f'PlayResX: {W}',
        f'PlayResY: {H}',
        'WrapStyle: 2',
        '',
        '[V4+ Styles]',
        'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
        'Style: Caption,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,5,2,2,90,90,250,1',
        'Style: Headline,DejaVu Sans,70,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,5,2,8,70,70,150,1',
        '',
        '[Events]',
        'Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text'
    ]
    def ts(x):
        cs=max(0,int(round(float(x)*100)))
        h=cs//360000; cs%=360000
        m=cs//6000; cs%=6000
        s=cs//100; c=cs%100
        return f'{h}:{m:02d}:{s:02d}.{c:02d}'
    for i,s in enumerate(plan):
        start=float(s['start']); end=float(s['end'])
        headline=str(s.get('headline') or '').strip()
        if headline:
            lines.append(f"Dialogue: 0,{ts(start)},{ts(min(end,start+0.9))},Headline,,0,0,0,,{_ass_escape(headline.upper())}")
        chunks=_caption_chunks(str(s.get('speech') or ''))
        if not chunks:
            continue
        dur=max(.2,end-start)
        weights=[max(1,len(x.split())) for x in chunks]
        total=max(1,sum(weights))
        cursor=start
        for j,(chunk,w) in enumerate(zip(chunks,weights)):
            a=cursor
            b=end if j==len(chunks)-1 else min(end, cursor + dur*w/total)
            cursor=b
            lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},Caption,,0,0,0,,{_ass_escape(chunk.upper())}")
    path.write_text('\n'.join(lines),encoding='utf-8')


def _visual_input(item: dict) -> str:
    p=str(item.get('cache_image') or '')
    return p if p and Path(p).is_file() else ''


def render_fast_premium(out: Path) -> dict:
    wall_start=time.perf_counter()
    story=next(x for x in catalog() if x.get('production_ready'))
    genre=story.get('genre','space')
    plan=make_plan(story)
    creative_quality_gate(story,plan)
    assets=asset_manifest(story,plan)
    resolved=prepare_media_cache(resolve_assets(assets))
    resolved=acquire_story_media(resolved)
    asset_report=asset_resolution_gate(resolved)
    verified=sum(1 for x in resolved if x.get('provider')=='wikimedia-commons')
    required=sum(1 for x in resolved if x.get('strategy')=='external-verified')
    if not required or verified != required:
        raise RuntimeError(f'Fast premium gate rejected media {verified}/{required}')
    for shot,item in zip(plan,resolved):
        shot['resolved_asset']=item

    duration=voice_plan(plan,genre,max_duration=float(story.get('target_duration_max',36)),
                        voice_name=str(story.get('voice_profile') or 'af_heart'),
                        voice_speed=float(story.get('voice_speed') or 1.09))

    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    ff=get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix='astra_fast_') as td:
        td=Path(td)
        audio=td/'mix.wav'
        audio_info=score_audio(plan,duration,genre,audio)
        ass=td/'captions.ass'; _write_ass(plan,ass)
        clips=[]
        for i,(shot,item) in enumerate(zip(plan,resolved)):
            src=_visual_input(item)
            dur=max(.25,float(shot['duration']))
            if not src:
                # Procedural/mechanism beats need no external media. Render exactly
                # one representative Studio frame, then animate it natively in FFmpeg.
                still=td/f'scene-{i:02d}-procedural.png'
                # Build a clean visual-only still. Do not call render_frame here:
                # that would bake Studio headlines/captions into the still and then
                # duplicate them when ASS captions are added later.
                u=min(dur*.45, max(.1,dur-.1))
                im=background(genre).copy()
                draw_visual(im,shot,float(shot['start'])+u,u,THEMES[genre][2])
                im.save(still,'PNG')
                src=str(still)
            frames=max(1,int(math.ceil(dur*FPS)))
            clip=td/f'scene-{i:02d}.mp4'
            # FFmpeg-native scale/crop + Ken Burns motion. No Python frame loop.
            motion=i % 4
            if motion==0:
                xexpr="'iw/2-(iw/zoom/2)'"; yexpr="'ih/2-(ih/zoom/2)'"
            elif motion==1:
                xexpr="'max(0,(iw-iw/zoom)*on/max(1,d-1))'"; yexpr="'ih/2-(ih/zoom/2)'"
            elif motion==2:
                xexpr="'max(0,(iw-iw/zoom)*(1-on/max(1,d-1)))'"; yexpr="'ih/2-(ih/zoom/2)'"
            else:
                xexpr="'iw/2-(iw/zoom/2)'"; yexpr="'max(0,(ih-ih/zoom)*on/max(1,d-1))'"
            vf=(
                f"scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,"
                f"zoompan=z='min(zoom+0.0016,1.075)':"
                f"x={xexpr}:y={yexpr}:"
                f"d={frames}:s=1080x1920:fps={FPS},"
                f"format=yuv420p"
            )
            cmd=[ff,'-hide_banner','-loglevel','error','-y','-loop','1','-i',src,
                 '-vf',vf,'-t',f'{dur:.3f}','-an','-c:v','libx264','-preset','veryfast',
                 '-crf','19','-pix_fmt','yuv420p',str(clip)]
            subprocess.run(cmd,check=True)
            clips.append(clip)

        concat=td/'concat.txt'
        concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in clips),encoding='utf-8')
        silent=td/'silent.mp4'
        subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
                        '-i',str(concat),'-c','copy',str(silent)],check=True)

        # Burn ASS captions and mux the already-generated neural voice/music mix.
        ass_filter=str(ass).replace('\\','/').replace(':','\\:')
        cmd=[ff,'-hide_banner','-loglevel','error','-y','-i',str(silent),'-i',str(audio),
             '-vf',f"ass='{ass_filter}'",'-map','0:v','-map','1:a','-c:v','libx264',
             '-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
             '-af','loudnorm=I=-14:TP=-1.0:LRA=7','-movflags','+faststart','-shortest',str(out)]
        subprocess.run(cmd,check=True)

    wall_seconds=round(time.perf_counter()-wall_start,3)
    return {
        'renderer':'ffmpeg-native-premium-v2',
        'duration':round(duration,3),
        'render_wall_seconds':wall_seconds,
        'realtime_factor':round(wall_seconds/max(duration,.001),3),
        'resolution':[W,H],
        'fps':FPS,
        'verified_subject_media':verified,
        'required_subject_media':required,
        'zero_cost':asset_report.get('zero_cost',False),
        'audio':audio_info,
        'output_bytes':out.stat().st_size,
    }


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    report=render_fast_premium(a.out)
    a.out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
