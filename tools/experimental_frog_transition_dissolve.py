"""Build and validate an optional two-frame dip-to-dusk rescue-to-plant handoff.

No changes to the canonical 32-frame render, its independent evidence or
publication gates. All 32 decoded action frames are preserved in order.
The only additional pixels are two derived bridge frames plus six exact
copies of the original final sprout frame. CPU/FFmpeg only; review-only.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tools.experimental_frog_payoff_hold import (
    CANONICAL_FRAMES, HOLD_FRAMES, FPS, file_sha256, frame_hashes, probe_video,
)

WIDTH, HEIGHT = 384, 576
FRAME_BYTES = WIDTH * HEIGHT * 3 // 2
BRIDGE_AFTER = 21
BRIDGE_FRAMES = 2


def decoded_yuv_frames(path):
    proc = subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path),
         '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-'],
        check=True, capture_output=True, timeout=90,
    )
    data = proc.stdout
    if len(data) != FRAME_BYTES * CANONICAL_FRAMES:
        raise ValueError('Source must contain exactly 32 YUV420p frames')
    return [data[i * FRAME_BYTES:(i + 1) * FRAME_BYTES]
            for i in range(CANONICAL_FRAMES)]


def blend_frame(first, second, numerator, denominator):
    if len(first) != FRAME_BYTES or len(second) != FRAME_BYTES:
        raise ValueError('Incorrect frame length for dissolve')
    if not 0 < numerator < denominator:
        raise ValueError('Dissolve weight must be strictly between 0 and 1')
    return bytes((a * (denominator - numerator) +
                  b * numerator + denominator // 2) // denominator
                 for a, b in zip(first, second))


def expected_layout(source_frames):
    # Direct crossfading ghosted the frog, grate and captions. Dim each
    # shot toward the same dusk-black instead. Outgoing/incoming camera
    # views are NEVER double-exposed; canonical 32 frames stay untouched.
    neutral = bytes([16] * (WIDTH * HEIGHT) +
                    [128] * (WIDTH * HEIGHT // 2))
    bridge = [
        blend_frame(source_frames[BRIDGE_AFTER], neutral, 3, 5),
        blend_frame(neutral, source_frames[BRIDGE_AFTER + 1], 2, 5),
    ]
    return (source_frames[:BRIDGE_AFTER + 1] + bridge +
            source_frames[BRIDGE_AFTER + 1:] +
            [source_frames[-1]] * HOLD_FRAMES), bridge


def frame_md5(frame):
    return hashlib.md5(frame).hexdigest()


def checks_for_hashes(original_hashes, extended_hashes, bridge_hashes):
    total = CANONICAL_FRAMES + BRIDGE_FRAMES + HOLD_FRAMES
    if len(original_hashes) != CANONICAL_FRAMES or len(extended_hashes) != total:
        return {'all_action_frames_preserved_exactly': False,
                'dusk_dip_interpolations_exact': False,
                'ending_hold_pixel_exact': False}
    indices = [(i, i if i <= BRIDGE_AFTER else i + BRIDGE_FRAMES)
               for i in range(CANONICAL_FRAMES)]
    return {
        'all_action_frames_preserved_exactly': all(
            extended_hashes[j] == original_hashes[i] for i, j in indices
        ),
        'dusk_dip_interpolations_exact': (
            extended_hashes[BRIDGE_AFTER + 1:
                            BRIDGE_AFTER + 1 + BRIDGE_FRAMES] ==
            bridge_hashes and
            len(set(bridge_hashes + [original_hashes[BRIDGE_AFTER],
                                      original_hashes[BRIDGE_AFTER + 1]])) == 4
        ),
        'ending_hold_pixel_exact': (
            extended_hashes[-HOLD_FRAMES:] ==
            [original_hashes[-1]] * HOLD_FRAMES
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    args = parser.parse_args()
    source = args.directory.resolve()
    dest = args.output_directory.resolve()
    if dest == source or source in dest.parents:
        raise ValueError('Optional dissolve must be outside canonical evidence')

    review = json.loads((source / 'review.json').read_text())
    verified = json.loads((source / 'story_review_verification.json').read_text())
    manifest = json.loads((source / 'story_review_manifest.json').read_text())
    assert review['success'] is True and all(review['checks'].values())
    assert len(review['frames']) == CANONICAL_FRAMES and review['fps'] == FPS
    assert verified['passed'] is True and all(verified['checks'].values())
    assert manifest['technical_evidence_passed'] is True
    assert manifest['video_frame_content_evidence']['passed'] is True
    for item in (review, verified, manifest):
        for flag in ('approved','published','production_ready','paid_apis_used'):
            assert item[flag] is False, flag
    assert review['frames'][BRIDGE_AFTER]['phase'] == 'rescue'
    assert review['frames'][BRIDGE_AFTER + 1]['phase'] == 'plant'
    assert review['frames'][BRIDGE_AFTER]['seed_xyz'] == (
        review['frames'][BRIDGE_AFTER + 1]['seed_xyz']
    ), 'Seed must remain continuous across the original cut'
    video = source / 'frog_story_previs.mp4'
    src_probe = probe_video(video)
    assert src_probe['fps'] == f'{FPS}/1'
    assert src_probe['frames'] == CANONICAL_FRAMES
    assert abs(src_probe['duration'] - CANONICAL_FRAMES / FPS) < .015
    assert file_sha256(video) == manifest['sha256'][video.name]
    src_hashes = frame_hashes(video)
    frames = decoded_yuv_frames(video)
    assert [frame_md5(f) for f in frames] == src_hashes

    extended, bridge = expected_layout(frames)
    bridge_hashes = [frame_md5(f) for f in bridge]
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / 'frog_story_transition_dip_review_only.mp4'
    result = subprocess.run(
        ['ffmpeg','-hide_banner','-loglevel','error','-y',
         '-f','rawvideo','-pix_fmt','yuv420p',
         '-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),
         '-i','pipe:0','-c:v','libx264','-preset','veryfast',
         '-qp','0','-pix_fmt','yuv420p',str(target)],
        input=b''.join(extended), capture_output=True, timeout=90,
    )
    result.check_returncode()
    actual_hashes = frame_hashes(target)
    actual_probe = probe_video(target)
    integrity = checks_for_hashes(src_hashes, actual_hashes, bridge_hashes)
    total = CANONICAL_FRAMES + BRIDGE_FRAMES + HOLD_FRAMES

    # Mutation checks make sure one broken canonical action, dissolve frame,
    # or held ending would be rejected by our independent output verifier.
    action_mutation = list(actual_hashes)
    action_mutation[20] = actual_hashes[19]
    bridge_mutation = list(actual_hashes)
    bridge_mutation[BRIDGE_AFTER + 1] = actual_hashes[BRIDGE_AFTER]
    payoff_mutation = list(actual_hashes)
    payoff_mutation[-1] = actual_hashes[-2 - HOLD_FRAMES]
    checks = {
        'source_manifest_and_evidence_preverified': True,
        'canonical_frame_and_fps_contract_intact': (
            src_probe['frames'] == CANONICAL_FRAMES and
            actual_probe['fps'] == src_probe['fps'] == f'{FPS}/1' and
            actual_probe['frames'] == total and
            len(actual_hashes) == total
        ),
        'duration_is_six_and_two_thirds_seconds': (
            abs(actual_probe['duration'] - total / FPS) < .015
        ),
        'canonical_source_sha256_unchanged': (
            file_sha256(video) == manifest['sha256'][video.name]
        ),
        **integrity,
        'corrupted_action_rejected': not checks_for_hashes(
            src_hashes, action_mutation, bridge_hashes
        )['all_action_frames_preserved_exactly'],
        'corrupted_dissolve_rejected': not checks_for_hashes(
            src_hashes, bridge_mutation, bridge_hashes
        )['dusk_dip_interpolations_exact'],
        'corrupted_ending_rejected': not checks_for_hashes(
            src_hashes, payoff_mutation, bridge_hashes
        )['ending_hold_pixel_exact'],
    }
    report = {
        'kind': 'astra_frog_optional_rescue_plant_dusk_dip',
        'source_frame_count': CANONICAL_FRAMES,
        'new_transition_frames': BRIDGE_FRAMES,
        'new_payoff_hold_frames': HOLD_FRAMES,
        'fps': FPS,
        'source_duration_seconds': src_probe['duration'],
        'extended_duration_seconds': actual_probe['duration'],
        'source_video_sha256': file_sha256(video),
        'extended_video_sha256': file_sha256(target),
        'checks': checks, 'passed': all(checks.values()),
        'canonical_review_unmodified': True,
        'semantic_quality': 'not_verified',
        'cinematic_quality': 'manual_review_required',
        'manual_visual_review_required': True,
        'approved': False, 'published': False, 'production_ready': False,
        'paid_apis_used': False,
        'note': ('Short dim-to-dusk cut avoids double-exposing moving subjects; '
                 'this is still an optional human-review edit, not published '
                 'quality or replacement canonical evidence.'),
    }
    (dest / 'transition_dip_review.json').write_text(
        json.dumps(report, indent=2) + '\n'
    )
    print('ASTRA_FROG_TRANSITION_DIP=' + json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
