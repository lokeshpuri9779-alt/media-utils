"""Assemble licensed scene clips into one video, without changing publishing workflows.

Manifest JSON: {"scenes":[{"path":"scene1.mp4","license":"owned"}, ...]}
Paths are relative to manifest directory. License labels are audit metadata, not proof.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def assemble(manifest, output):
    manifest = Path(manifest).resolve()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    scenes = data.get('scenes', [])
    if not 2 <= len(scenes) <= 100:
        raise ValueError('Expected 2-100 scenes')
    paths = []
    for scene in scenes:
        if not scene.get('license') or not scene.get('path'):
            raise ValueError('Each scene requires path and license provenance')
        path = (manifest.parent / scene['path']).resolve()
        if not path.is_file() or path.suffix.lower() != '.mp4':
            raise ValueError(f'Missing MP4: {path}')
        paths.append(path)
    output = Path(output).resolve()
    if output in paths:
        raise ValueError('Output cannot overwrite an input')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        normalized = []
        target_width = int(data.get('width', 720))
        target_height = int(data.get('height', 1280))
        if (target_width, target_height) not in {(720,1280),(1280,720),(1080,1920),(1920,1080)}:
            raise ValueError('Unsupported canvas')
        for index, path in enumerate(paths):
            target = Path(tmp) / f'{index:04d}.mp4'
            subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                '-i',str(path),'-map','0:v:0','-an','-vf',f'scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},fps=24,format=yuv420p',
                '-c:v','libx264','-preset','veryfast','-crf','21',str(target)],
                check=True,timeout=300)
            normalized.append(target)
        concat = Path(tmp) / 'concat.txt'
        concat.write_text(''.join("file '" + str(p) + "'\\n" for p in normalized))
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
            '-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags',
            '+faststart',str(output)],check=True,timeout=300)
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError('Empty output')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    print(assemble(args.manifest,args.output))
