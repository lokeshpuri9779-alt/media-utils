"""Offline media QA for the independent Meta ASTRA lane. No uploads."""
import argparse
import json
import subprocess
from pathlib import Path


def probe(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Missing or empty video')
    result = subprocess.run(['ffprobe','-v','error','-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
        '-of','json',str(path)],capture_output=True,text=True,check=True,timeout=30)
    data = json.loads(result.stdout)
    video = next((s for s in data.get('streams',[]) if s.get('codec_type')=='video'),None)
    if video is None:
        raise ValueError('No video stream')
    duration = float(data['format']['duration'])
    if not 0.5 <= duration <= 7200:
        raise ValueError('Unexpected duration')
    if video.get('codec_name') != 'h264':
        raise ValueError('Expected H.264')
    width, height = video.get('width'), video.get('height')
    if (width,height) not in {(720,1280),(1280,720),(1080,1920),(1920,1080)}:
        raise ValueError('Unexpected dimensions')
    return {'passed':True,'duration_seconds':duration,'width':width,'height':height,
            'has_audio':any(s.get('codec_type')=='audio' for s in data['streams'])}

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('video')
    args=p.parse_args()
    print(json.dumps(probe(args.video),indent=2))
