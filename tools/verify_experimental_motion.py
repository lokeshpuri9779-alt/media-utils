"""Verify real experimental output artifacts; reject blank/still animation.
No YouTube access and no production integration.
"""
import argparse,json,subprocess
from pathlib import Path

def probe_video(path):
    path=Path(path)
    cmd=['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,nb_frames,avg_frame_rate','-show_entries','format=duration','-of','json',str(path)]
    data=json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=30).stdout)
    stream=(data.get('streams') or [{}])[0]
    duration=float(data.get('format',{}).get('duration') or 0)
    if not path.is_file() or path.stat().st_size<1000 or duration<2 or int(stream.get('width') or 0)<320:
        raise ValueError('missing, short, or invalid video')
    # FFmpeg scene detector is deliberately conservative: no visual changes means
    # the animation should not pass merely because the MP4 was encoded.
    cmd=['ffmpeg','-hide_banner','-loglevel','info','-i',str(path),'-vf','select=gt(scene\\,0.015),showinfo','-an','-f','null','-']
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError(result.stderr[-1200:])
    changed=result.stderr.count('showinfo')
    return {'path':str(path),'duration_seconds':duration,'width':int(stream['width']),
            'height':int(stream['height']),'scene_change_log_lines':changed,
            'visual_change_detected':changed>0,'pass':changed>0}

def main():
    p=argparse.ArgumentParser();p.add_argument('video',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args()
    try:report=probe_video(a.video)
    except Exception as e:report={'path':str(a.video),'pass':False,'error':f'{type(e).__name__}: {e}'}
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(report,indent=2)+'\\n')
    print(json.dumps(report,indent=2))
    if not report['pass']:raise SystemExit(1)

if __name__=='__main__':main()
