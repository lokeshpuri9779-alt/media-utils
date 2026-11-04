"""Produce a separately verified, review-only held ending of the frog preview.

The 32-frame canonical Blender sequence, its technical review evidence,
and all editorial/publishing gates remain unchanged. This is an optional cut.
Requires only local FFmpeg/ffprobe; no paid APIs or external resources.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CANONICAL_FRAMES = 32
HOLD_FRAMES = 6
FPS = 6


def command(*argv):
    result = subprocess.run(
        list(map(str, argv)), capture_output=True, text=True,
        check=True, timeout=90,
    )
    return result.stdout


def frame_hashes(path):
    output = command(
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', path,
        '-map', '0:v:0', '-f', 'framemd5', '-',
    )
    return [line.split(',')[-1].strip() for line in output.splitlines()
            if line and not line.startswith('#')]


def file_sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def probe_video(path):
    result = command(
        'ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
        '-show_entries', 'stream=avg_frame_rate,nb_read_frames',
        '-show_entries', 'format=duration', '-of', 'json', path,
    )
    parsed = json.loads(result)
    return {
        'fps': parsed['streams'][0]['avg_frame_rate'],
        'frames': int(parsed['streams'][0]['nb_read_frames']),
        'duration': float(parsed['format']['duration']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    source_root = args.directory.resolve()
    dest_root = args.output_directory.resolve()
    if source_root == dest_root or source_root in dest_root.parents:
        raise ValueError('Held review must be outside canonical review directory')

    review = json.loads((source_root / 'review.json').read_text())
    verification = json.loads((source_root / 'story_review_verification.json').read_text())
    manifest = json.loads((source_root / 'story_review_manifest.json').read_text())
    assert review['success'] is True and all(review['checks'].values())
    assert len(review['frames']) == CANONICAL_FRAMES and review['fps'] == FPS
    assert verification['passed'] is True and all(verification['checks'].values())
    assert manifest['technical_evidence_passed'] is True
    assert manifest['video_frame_content_evidence']['passed'] is True
    for item in (review, verification, manifest):
        for field in ('approved', 'published', 'production_ready', 'paid_apis_used'):
            assert item[field] is False, f'{field} must remain false'

    source_video = source_root / 'frog_story_previs.mp4'
    source_probe = probe_video(source_video)
    assert source_probe['fps'] == f'{FPS}/1'
    assert source_probe['frames'] == CANONICAL_FRAMES
    assert abs(source_probe['duration'] - CANONICAL_FRAMES / FPS) < .015
    original = frame_hashes(source_video)
    assert len(original) == CANONICAL_FRAMES

    dest_root.mkdir(parents=True, exist_ok=True)
    held_video = dest_root / 'frog_story_payoff_hold_review_only.mp4'
    command(
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', source_video,
        '-vf', f'tpad=stop_mode=clone:stop_duration={HOLD_FRAMES / FPS}',
        '-c:v', 'libx264', '-preset', 'veryfast', '-qp', '0',
        '-pix_fmt', 'yuv420p', '-r', str(FPS), held_video,
    )
    held_probe = probe_video(held_video)
    hashes = frame_hashes(held_video)
    checks = {
        'canonical_review_preverified': True,
        'canonical_fps_and_frame_count_preserved': (
            held_probe['fps'] == source_probe['fps'] == f'{FPS}/1' and
            held_probe['frames'] == CANONICAL_FRAMES + HOLD_FRAMES and
            len(hashes) == CANONICAL_FRAMES + HOLD_FRAMES
        ),
        'all_32_action_frames_pixel_exact': hashes[:CANONICAL_FRAMES] == original,
        'six_payoff_frames_pixel_exact_to_last_frame': (
            hashes[CANONICAL_FRAMES:] == [original[-1]] * HOLD_FRAMES
        ),
        'duration_is_six_and_one_third_seconds': (
            abs(held_probe['duration'] - (CANONICAL_FRAMES + HOLD_FRAMES)/FPS) < .015
        ),
        'source_sequence_and_proof_unmodified': (
            file_sha256(source_video) == manifest['sha256'].get(source_video.name)
        ),
    }
    report = {
        'kind': 'astra_frog_optional_payoff_hold_review',
        'source_profile': 'frog',
        'source_frame_count': CANONICAL_FRAMES,
        'additional_held_frames': HOLD_FRAMES,
        'fps': FPS,
        'source_duration_seconds': source_probe['duration'],
        'held_duration_seconds': held_probe['duration'],
        'source_video_sha256': file_sha256(source_video),
        'held_video_sha256': file_sha256(held_video),
        'checks': checks,
        'passed': all(checks.values()),
        'manual_visual_review_required': True,
        'semantic_quality': 'not_verified',
        'cinematic_quality': 'manual_review_required',
        'approved': False, 'published': False, 'production_ready': False,
        'paid_apis_used': False,
        'note': ('Optional pacing experiment, not the authoritative 32-frame '
                 'technical evidence or an editorial approval.'),
    }
    (dest_root / 'payoff_hold_review.json').write_text(
        json.dumps(report, indent=2) + '\n'
    )
    print('ASTRA_FROG_PAYOFF_HOLD=' + json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
