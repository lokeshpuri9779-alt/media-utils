"""Validate experimental MP4 structure and actual changing frames (no publishing)."""
import argparse,json,subprocess
from pathlib import Path

def probe_video(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size<1000:
        raise ValueError('missing or empty video')
    cmd=['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-show_entries','format=duration','-of','json',str(path)]
    data=json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=30).stdout)
    stream=(data.get('streams') or [{}])[0]
    duration=float(data.get('format',{}).get('duration') or 0)
    width=int(stream.get('width') or 0);height=int(stream.get('height') or 0)
    if duration<2 or width<320 or height<320:
        raise ValueError('video duration or resolution too small')
    # Sample frames at 2 fps and hash their decoded grayscale pixels.
    # Unlike scene-cut detection, this also detects smooth character movement.
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),
         '-vf','fps=2,scale=64:64,format=gray','-an','-f','framemd5','-']
    result=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=60)
    frame_lines=[line for line in result.stdout.splitlines() if line.strip() and not line.startswith('#')]
    hashes=[line.rsplit(',',1)[-1].strip() for line in frame_lines]
    unique=len(set(hashes))
    # Minimum 3 distinct sampled frames avoids accepting static encoded videos.
    passed=len(hashes)>=4 and unique>=3
    return {'path':str(path),'duration_seconds':duration,'width':width,'height':height,
            'sampled_frames':len(hashes),'unique_frame_hashes':unique,
            'visual_change_detected':unique>=3,'pass':passed,
            'quality_verified':False,'published':False}

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
