"""Supervised review-only SDXL load/compile; optional one-image diagnostic."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

MODEL = 'OpenVINO/stable-diffusion-xl-base-1.0-int8-ov'
REVISION = 'd54e5b43fcb6b4b358f3a134269115d3fcb3eb25'
OUT = Path('artifacts/experimental-openvino/sdxl-load')
ROOT = Path('/tmp/astra-sdxl-int8')
GIB = 1024 ** 3
ONE_IMAGE_SEED = 42
ONE_IMAGE_STEPS = 20
ONE_IMAGE_PROMPT = ('family-friendly illustration of a single bright red toy fire truck, '
    'side view, fully visible, on a plain white background, clear colorful detailed '
    'shapes, no people, no text')
ONE_IMAGE_NEGATIVE_PROMPT = 'people, text, words, watermark, logo, blurry, deformed wheels, missing ladder'

def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / (name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(OUT / name)

def stage(name):
    save('stage.json', {'stage': name, 'started': time.time()})

def selected(name):
    if name in ('model_index.json', 'scheduler/scheduler_config.json'):
        return True
    parts = name.split('/')
    if len(parts) != 2:
        return False
    group, file = parts
    if group in ('text_encoder', 'text_encoder_2', 'unet', 'vae_decoder', 'vae_encoder'):
        return file in ('config.json', 'openvino_model.bin', 'openvino_model.xml')
    return group in ('tokenizer', 'tokenizer_2') and file in (
        'merges.txt', 'vocab.json', 'tokenizer_config.json', 'special_tokens_map.json')

def worker(one_image=False):
    stage('download')
    started = time.monotonic()
    url = f'https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true'
    with urllib.request.urlopen(url, timeout=30) as r:
        metadata = json.load(r)
    if metadata['sha'] != REVISION:
        raise ValueError('Revision mismatch')
    files = [f for f in metadata['siblings'] if selected(f['rfilename'])]
    if len(files) != 25:
        raise ValueError(f'Unexpected manifest: {len(files)} files')
    total = sum(f['size'] for f in files)
    import shutil
    if shutil.disk_usage('/tmp').free < 2 * total + 2 * GIB:
        raise RuntimeError('Insufficient disk before download')
    manifest = []
    for f in files:
        path = ROOT / f['rfilename']
        path.parent.mkdir(parents=True, exist_ok=True)
        sha256 = hashlib.sha256()
        git_hash = hashlib.sha1(f"blob {f['size']}\0".encode())
        count = 0
        with urllib.request.urlopen(f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{f['rfilename']}", timeout=45) as r, path.open('wb') as out:
            while chunk := r.read(1024 * 1024):
                count += len(chunk)
                if count > f['size']:
                    raise ValueError('Download exceeds expected size')
                out.write(chunk)
                sha256.update(chunk)
                git_hash.update(chunk)
        expected = f.get('lfs', {}).get('sha256')
        if count != f['size'] or (sha256.hexdigest() != expected if expected else git_hash.hexdigest() != f['blobId']):
            raise ValueError(f"Integrity mismatch: {f['rfilename']}")
        manifest.append({'path': f['rfilename'], 'bytes': count, 'sha256': sha256.hexdigest(), 'verified_against': 'lfs_sha256' if expected else 'git_blob_sha1'})
    save('manifest.json', manifest)
    timings = {'download_seconds': time.monotonic() - started}
    stage('load')
    started = time.monotonic()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from optimum.intel import OVStableDiffusionXLPipeline
    config = {'INFERENCE_PRECISION_HINT': 'f32', 'PERFORMANCE_HINT': 'LATENCY', 'NUM_STREAMS': '1'}
    pipe = OVStableDiffusionXLPipeline.from_pretrained(
        str(ROOT), export=False, compile=False, device='CPU', local_files_only=True,
        trust_remote_code=False, load_in_8bit=False, ov_config=config,
    )
    timings['load_seconds'] = time.monotonic() - started
    save('timings.json', timings)
    stage('compile')
    started = time.monotonic()
    pipe.reshape(batch_size=1, height=512 if one_image else 1024, width=512 if one_image else 1024, num_images_per_prompt=1)
    pipe.compile()
    timings['compile_seconds'] = time.monotonic() - started
    save('timings.json', timings)
    result_status = 'loaded_and_compiled'
    images_generated = 0
    if one_image:
        stage('inference')
        started = time.monotonic()
        import torch
        import numpy as np
        noise = torch.randn((1, 4, 64, 64),
            generator=torch.Generator(device='cpu').manual_seed(ONE_IMAGE_SEED),
            dtype=torch.float32)
        np.save(OUT / 'initial-latents.npy', noise.numpy(), allow_pickle=False)
        save('scheduler.json', dict(pipe.scheduler.config))
        save('request.json', {'seed': ONE_IMAGE_SEED, 'steps': ONE_IMAGE_STEPS,
            'prompt': ONE_IMAGE_PROMPT, 'negative_prompt': ONE_IMAGE_NEGATIVE_PROMPT,
            'guidance_scale': 7.5, 'width': 512, 'height': 512,
            'scheduler': type(pipe.scheduler).__name__,
            'latent_sha256': hashlib.sha256(noise.numpy().tobytes()).hexdigest(),
            'approved': False, 'production_ready': False, 'published': False,
            'manual_visual_review_required': True})
        generated = pipe(
            ONE_IMAGE_PROMPT, negative_prompt=ONE_IMAGE_NEGATIVE_PROMPT,
            height=512, width=512, num_inference_steps=ONE_IMAGE_STEPS,
            guidance_scale=7.5,
            latents=noise, output_type='pil')
        if len(generated.images) != 1 or generated.images[0].size != (512, 512):
            raise ValueError('Expected exactly one 512x512 diagnostic image')
        location = OUT / 'sdxl-fixed-seed-42.png'
        generated.images[0].save(location, format='PNG')
        timings['inference_seconds'] = time.monotonic() - started
        save('timings.json', timings)
        save('image-review.json', {
            'model': MODEL, 'revision': REVISION, 'seed': ONE_IMAGE_SEED,
            'steps': ONE_IMAGE_STEPS, 'prompt': ONE_IMAGE_PROMPT,
            'negative_prompt': ONE_IMAGE_NEGATIVE_PROMPT,
            'width': 512, 'height': 512,
            'sha256': hashlib.sha256(location.read_bytes()).hexdigest(),
            'file': location.name, 'approved': False, 'production_ready': False,
            'published': False, 'semantic_quality': 'not_verified',
            'character_consistency': 'not_verified',
            'manual_visual_review_required': True})
        result_status = 'image_generated_review_only'
        images_generated = 1
    save('worker-result.json', {'status': result_status, 'ov_config': config,
        'shape': {'batch': 1, 'height': 512 if one_image else 1024, 'width': 512 if one_image else 1024},
        'packages': {p: importlib.metadata.version(p) for p in ('openvino', 'optimum-intel', 'diffusers', 'transformers', 'torch', 'psutil')},
        'images_generated': images_generated})

def available_memory():
    import psutil
    available = psutil.virtual_memory().available
    root = Path('/sys/fs/cgroup')
    if (root / 'memory.max').exists():
        maximum = (root / 'memory.max').read_text().strip()
        if maximum != 'max':
            available = min(available, max(0, int(maximum) - int((root / 'memory.current').read_text())))
    return available

def limit_reason(rss, available, elapsed, load_elapsed, inference_elapsed=None):
    if rss >= 12 * GIB:
        return 'rss_limit'
    if available < 2 * GIB:
        return 'available_ram_limit'
    if load_elapsed is not None and load_elapsed >= 600:
        return 'load_compile_timeout'
    if inference_elapsed is not None and inference_elapsed >= 600:
        return 'inference_timeout'
    if elapsed >= 1200:
        return 'overall_timeout'
    return None

def supervise(one_image=False):
    import psutil
    import shutil
    OUT.mkdir(parents=True, exist_ok=True)
    # Refuse stale evidence, preventing an earlier success from being reused.
    if (OUT / 'stage.json').exists() or (OUT / 'worker-result.json').exists():
        raise RuntimeError('Output directory already contains a prior attempt')
    report = {'model': MODEL, 'revision': REVISION, 'approved': False,
        'production_ready': False, 'published': False, 'manual_visual_review_required': True,
        'semantic_quality': 'not_verified', 'character_consistency': 'not_verified',
        'images_generated': 0, 'mode': 'single_image' if one_image else 'load_only',
        'run_id': os.getenv('GITHUB_RUN_ID'), 'commit': os.getenv('GITHUB_SHA'),
        'initial_available_ram_bytes': available_memory(), 'initial_disk_free_bytes': shutil.disk_usage('/tmp').free,
        'limits': {'rss_bytes': 12 * GIB, 'minimum_available_ram_bytes': 2 * GIB,
                   'load_compile_seconds': 600, 'inference_seconds': 600, 'overall_seconds': 1200},
        'peak_rss_bytes_by_stage': {}, 'rss_measurement': 'sampled process-tree RSS every 0.2 seconds; shared pages may be counted more than once'}
    save('report.json', {**report, 'status': 'started'})
    started = time.monotonic()
    load_started = None
    inference_started = None
    reason = None
    with (OUT / 'worker.log').open('w') as log:
        command = [sys.executable, '-m', 'tools.experimental_sdxl_load', '--worker']
        if one_image:
            command.append('--one-image')
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while process.poll() is None:
            try:
                current = json.loads((OUT / 'stage.json').read_text())['stage']
            except FileNotFoundError:
                current = 'startup'
            if current in ('load', 'compile') and load_started is None:
                load_started = time.monotonic()
            if current == 'inference' and inference_started is None:
                inference_started = time.monotonic()
            try:
                root = psutil.Process(process.pid)
                rss = sum(p.memory_info().rss for p in [root] + root.children(recursive=True) if p.is_running())
            except psutil.NoSuchProcess:
                rss = 0
            report['peak_rss_bytes_by_stage'][current] = max(report['peak_rss_bytes_by_stage'].get(current, 0), rss)
            now = time.monotonic()
            reason = limit_reason(rss, available_memory(), now - started,
                now - load_started if current in ('load', 'compile') and load_started is not None else None,
                now - inference_started if current == 'inference' and inference_started is not None else None)
            if reason:
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(0.2)
        code = process.wait()
    expected = 'image_generated_review_only' if one_image else 'loaded_and_compiled'
    result = json.loads((OUT / 'worker-result.json').read_text()) if (OUT / 'worker-result.json').exists() else {}
    success = code == 0 and result.get('status') == expected and (
        not one_image or ((OUT / 'image-review.json').exists() and (OUT / 'sdxl-fixed-seed-42.png').exists()))
    report.update(status=reason or (expected if success else 'worker_failed'),
                  images_generated=result.get('images_generated', 0) if success else 0,
                  worker_exit_code=code, elapsed_seconds=time.monotonic() - started)
    save('report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == expected else 1

if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker(one_image='--one-image' in sys.argv)
    else:
        raise SystemExit(supervise(one_image='--one-image' in sys.argv))
