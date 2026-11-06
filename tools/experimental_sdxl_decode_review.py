"""One bounded, CPU-only reference VAE decode of the saved run-76 latent."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

from tools.experimental_sdxl_load import GIB, available_memory, limit_reason

SOURCE = Path('artifacts/experimental-openvino/sdxl-source')
OUT = Path('artifacts/experimental-openvino/sdxl-decode-review')
ROOT = Path('/tmp/astra-sdxl-reference-vae')
SOURCE_RUN = '41988573278'
SOURCE_COMMIT = 'c26da903fc75045deaa181f6ac10c26c9ec4ebe7'
OV_MODEL = 'OpenVINO/stable-diffusion-xl-base-1.0-int8-ov'
OV_REVISION = 'd54e5b43fcb6b4b358f3a134269115d3fcb3eb25'
REFERENCE_MODEL = 'stabilityai/stable-diffusion-xl-base-1.0'
REFERENCE_REVISION = '462165984030d82259a11f4367a4eed129e94a7b'
SCALE = 0.13025
GUARDS = {'approved': False, 'production_ready': False, 'published': False,
          'manual_visual_review_required': True,
          'semantic_quality': 'not_verified', 'character_consistency': 'not_verified'}
SOURCE_HASHES = {
    'denoised-latents.npy': 'fc53b74944c0b1b0c72f0a82743812677c8d34e1faa39d0fbac99e8f04f34c35',
    'denoised-latents.json': '59ee918d36ce83fcab4d32d87dcd109e5a466008bf90558e0ef77ede0147f7f8',
    'conditioning.json': '33880913a7c0b126b028cfc9465c0557388fab7b0b6d806d9e5c6bd7f07cd181',
    'request.json': '15e8f6ee362e658714ab007aa125f305c8761ff45fd0f6a14081f404dd514c2f',
    'report.json': 'b1447ef13586c4159eeac56afcb1f7b5aaef86bd4d5a0d9c31b4127f472f3644',
    'sdxl-fixed-seed-42.png': '4fb3557b1183d584d5e2645987182b9a0c2971079cc3d3e733c6cd1e97d40f0e',
}
# Files verified against the pinned HF revision's metadata during preflight.
DOWNLOADS = (
    (OV_MODEL, OV_REVISION, 'vae_decoder/config.json', 'ov-vae-config.json', 931,
     'd93c03a11ecbd4ecb37c9091e99575ca1b4c8c6302f027024c5570c58cd1f793'),
    (REFERENCE_MODEL, REFERENCE_REVISION, 'vae/config.json', 'vae/config.json', 642,
     '0b331c8ac22ded5f9997a144a575c1d113d6169aff262c353f39015bd24a6264'),
    (REFERENCE_MODEL, REFERENCE_REVISION, 'vae/diffusion_pytorch_model.safetensors',
     'vae/diffusion_pytorch_model.safetensors', 334643268,
     '1598f3d24932bcfe6634e8b618ea1e30ab1d57f5aad13a6d2de446d2199f2341'),
)
CONFIG_KEYS = ('_class_name', 'act_fn', 'block_out_channels', 'down_block_types',
               'force_upcast', 'in_channels', 'latent_channels', 'layers_per_block',
               'norm_num_groups', 'out_channels', 'sample_size', 'scaling_factor',
               'up_block_types')
CONFIG_DEFAULTS = {'latents_mean': None, 'latents_std': None, 'shift_factor': None,
                   'mid_block_add_attention': True, 'use_post_quant_conv': True,
                   'use_quant_conv': True}


def sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    temporary = OUT / (name + '.tmp')
    temporary.write_text(json.dumps({**data, **GUARDS}, indent=2) + '\n')
    temporary.replace(OUT / name)


def stage(name):
    save('stage.json', {'stage': name})


def validate_latents(array):
    import numpy as np
    if array.shape != (1, 4, 128, 128) or array.dtype != np.float32 or not np.isfinite(array).all():
        raise ValueError('Invalid source latent shape, dtype or finite values')


def validate_source():
    import numpy as np
    from PIL import Image
    for name, expected in SOURCE_HASHES.items():
        if sha256(SOURCE / name) != expected:
            raise ValueError(f'Source hash mismatch: {name}')
    metadata = json.loads((SOURCE / 'denoised-latents.json').read_text())
    expected = {'run_id': SOURCE_RUN, 'commit': SOURCE_COMMIT, 'model': OV_MODEL,
                'revision': OV_REVISION, 'steps_completed': 20, 'seed': 42,
                'scaling': 'raw_scheduler_output_unscaled', 'dtype': 'float32',
                'shape': [1, 4, 128, 128], 'approved': False,
                'production_ready': False, 'published': False,
                'manual_visual_review_required': True}
    if any(metadata.get(k) != v for k, v in expected.items()):
        raise ValueError('Source checkpoint provenance mismatch')
    condition = json.loads((SOURCE / 'conditioning.json').read_text())
    if condition['vae_scaling_factor'] != SCALE or condition['vae_scale_factor'] != 8:
        raise ValueError('Source scaling mismatch')
    with Image.open(SOURCE / 'sdxl-fixed-seed-42.png') as image:
        if image.size != (1024, 1024) or image.mode != 'RGB':
            raise ValueError('Unexpected baseline image')
        image.verify()
    array = np.load(SOURCE / 'denoised-latents.npy', allow_pickle=False)
    validate_latents(array)
    return array


def download_one(item, *, root=None):
    model, revision, remote, local, expected_size, expected_hash = item
    location = (ROOT if root is None else root) / local
    location.parent.mkdir(parents=True, exist_ok=True)
    temporary = location.with_name(location.name + '.tmp')
    digest = hashlib.sha256()
    size = 0
    url = f'https://huggingface.co/{model}/resolve/{revision}/{remote}'
    try:
        with urllib.request.urlopen(url, timeout=45) as response, temporary.open('wb') as handle:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > expected_size:
                    raise ValueError(f'Download exceeds pinned size: {remote}')
                digest.update(block)
                handle.write(block)
        if size != expected_size or digest.hexdigest() != expected_hash:
            raise ValueError(f'Download integrity mismatch: {remote}')
        temporary.replace(location)
    finally:
        temporary.unlink(missing_ok=True)
    return {'model': model, 'revision': revision, 'path': remote,
            'bytes': size, 'sha256': digest.hexdigest()}


def validate_configs(exported, reference):
    origin = exported.get('_name_or_path', '')
    if ('models--stabilityai--stable-diffusion-xl-base-1.0' not in origin or
            not origin.endswith(f'/snapshots/{REFERENCE_REVISION}/vae')):
        raise ValueError('Export does not identify the pinned reference VAE')
    if any(key not in reference or reference[key] != exported.get(key) for key in CONFIG_KEYS):
        raise ValueError('Reference/export VAE configuration mismatch')
    if (reference['_class_name'] != 'AutoencoderKL' or reference['scaling_factor'] != SCALE
            or reference['sample_size'] != 1024 or reference['latent_channels'] != 4):
        raise ValueError('Unexpected reference VAE configuration')
    for key, default in CONFIG_DEFAULTS.items():
        if exported.get(key, default) != default or reference.get(key, default) != default:
            raise ValueError(f'Unsupported VAE configuration: {key}')


def decode_latents(vae, array, torch):
    """Scale raw scheduler output once; do not alter the archived latent."""
    validate_latents(array)
    with torch.inference_mode():
        return vae.decode(torch.from_numpy(array.copy()) / SCALE, return_dict=False)[0]


def worker():
    started = time.monotonic()
    stage('validate')
    array = validate_source()
    stage('download')
    files = [download_one(item) for item in DOWNLOADS]
    exported = json.loads((ROOT / 'ov-vae-config.json').read_text())
    reference = json.loads((ROOT / 'vae/config.json').read_text())
    validate_configs(exported, reference)
    save('provenance.json', {
        'source_run': SOURCE_RUN, 'source_commit': SOURCE_COMMIT,
        'source_hashes': SOURCE_HASHES, 'files': files,
        'reference_model': REFERENCE_MODEL, 'reference_revision': REFERENCE_REVISION,
        'export_origin': exported['_name_or_path'], 'source_scaling': 'raw_scheduler_output_unscaled',
        'decode_operation': 'raw_latent / 0.13025; AutoencoderKL.decode; VaeImageProcessor.postprocess',
        'interpretation': 'Same recorded source VAE; FP32 reference versus INT8 export, not bit-identical weights.'})
    shutil.copyfile(ROOT / 'ov-vae-config.json', OUT / 'ov-vae-config.json')
    shutil.copyfile(ROOT / 'vae/config.json', OUT / 'reference-vae-config.json')
    stage('load')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    import torch
    import numpy as np
    from PIL import Image
    from diffusers import AutoencoderKL
    from diffusers.image_processor import VaeImageProcessor
    from tools.experimental_cpu_runtime_probe import collect
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    load_started = time.monotonic()
    vae, info = AutoencoderKL.from_pretrained(
        str(ROOT / 'vae'), torch_dtype=torch.float32, use_safetensors=True,
        local_files_only=True, low_cpu_mem_usage=False, output_loading_info=True)
    if any(info.get(key) for key in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')):
        raise ValueError(f'Incomplete reference VAE load: {info}')
    vae = vae.to(device='cpu', dtype=torch.float32).eval()
    vae.disable_tiling()
    vae.disable_slicing()
    validate_configs(exported, {**dict(vae.config), '_class_name': type(vae).__name__})
    save('runtime.json', {**collect(), 'device': 'cpu', 'dtype': str(vae.dtype),
        'torch_threads': torch.get_num_threads(), 'torch_interop_threads': torch.get_num_interop_threads(),
        'tiling': vae.use_tiling, 'slicing': vae.use_slicing,
        'packages': {p: importlib.metadata.version(p) for p in ('torch', 'diffusers', 'numpy', 'pillow', 'psutil')},
        'python': sys.version, 'cpu_affinity': sorted(os.sched_getaffinity(0))})
    load_seconds = time.monotonic() - load_started
    stage('decode')
    decode_started = time.monotonic()
    decoded = decode_latents(vae, array, torch)
    decode_seconds = time.monotonic() - decode_started
    if tuple(decoded.shape) != (1, 3, 1024, 1024) or not torch.isfinite(decoded).all().item():
        raise ValueError('Reference decode returned invalid pixels')
    image = VaeImageProcessor(vae_scale_factor=8).postprocess(decoded, output_type='pil')[0]
    image.save(OUT / 'reference-vae.png', format='PNG')
    shutil.copyfile(SOURCE / 'sdxl-fixed-seed-42.png', OUT / 'baseline-openvino.png')
    shutil.copyfile(SOURCE / 'denoised-latents.npy', OUT / 'source-latents.npy')
    with Image.open(SOURCE / 'sdxl-fixed-seed-42.png') as baseline:
        difference = np.asarray(image, dtype=np.float32) - np.asarray(baseline, dtype=np.float32)
    save('comparison.json', {'baseline_sha256': SOURCE_HASHES['sdxl-fixed-seed-42.png'],
        'reference_sha256': sha256(OUT / 'reference-vae.png'), 'width': 1024, 'height': 1024,
        'mean_absolute_pixel_difference_0_255': float(np.abs(difference).mean()),
        'root_mean_square_pixel_difference_0_255': float(np.sqrt((difference ** 2).mean())),
        'note': 'Diagnostic differences only: no automatic semantic pass or approval.'})
    save('worker-result.json', {'status': 'decode_completed_review_only', 'images_generated': 1,
        'denoising_steps_executed': 0, 'load_seconds': load_seconds,
        'decode_seconds': decode_seconds, 'worker_elapsed_seconds': time.monotonic() - started})


def run_bounded_worker(out, module, timed_stage):
    """Supervise an isolated review worker under the run-76 CPU memory limits."""
    import psutil
    started = time.monotonic()
    peaks = {}
    load_started = operation_started = None
    reason = None
    with (out / 'worker.log').open('w') as log:
        process = subprocess.Popen([sys.executable, '-m', module, '--worker'],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while process.poll() is None:
            current = json.loads((out / 'stage.json').read_text())['stage'] if (out / 'stage.json').exists() else 'startup'
            now = time.monotonic()
            if current == 'load' and load_started is None:
                load_started = now
            if current == timed_stage and operation_started is None:
                operation_started = now
            try:
                root = psutil.Process(process.pid)
                rss = sum(p.memory_info().rss for p in [root] + root.children(recursive=True) if p.is_running())
            except psutil.NoSuchProcess:
                rss = 0
            peaks[current] = max(peaks.get(current, 0), rss)
            reason = limit_reason(rss, available_memory(), now - started,
                now - load_started if current == 'load' and load_started is not None else None,
                now - operation_started if operation_started is not None else None,
                inference_limit=900, overall_limit=1200)
            if reason:
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(0.2)
        code = process.wait()
    return code, reason, time.monotonic() - started, peaks


def supervise():
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError('Output directory already contains a prior attempt')
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'mode': 'reference_vae_decode_only', 'source_run': SOURCE_RUN,
        'source_commit': SOURCE_COMMIT, 'run_id': os.getenv('GITHUB_RUN_ID'),
        'commit': os.getenv('GITHUB_SHA'), 'images_generated': 0, 'denoising_steps_executed': 0,
        'limits': {'rss_bytes': 12 * GIB, 'minimum_available_ram_bytes': 2 * GIB,
                   'load_compile_seconds': 600, 'decode_seconds': 900, 'overall_seconds': 1200},
        'peak_rss_bytes_by_stage': {},
        'rss_measurement': 'sampled process-tree RSS every 0.2 seconds; shared pages may be counted more than once'}
    save('report.json', {**report, 'status': 'started'})
    code, reason, elapsed, peaks = run_bounded_worker(OUT, 'tools.experimental_sdxl_decode_review', 'decode')
    report['peak_rss_bytes_by_stage'] = peaks
    result = json.loads((OUT / 'worker-result.json').read_text()) if (OUT / 'worker-result.json').exists() else {}
    success = (code == 0 and result.get('status') == 'decode_completed_review_only'
               and (OUT / 'reference-vae.png').exists() and (OUT / 'comparison.json').exists())
    report.update(status=reason or ('decode_completed_review_only' if success else 'worker_failed'),
                  worker_exit_code=code, elapsed_seconds=elapsed,
                  images_generated=1 if success else 0)
    save('report.json', report)
    print(json.dumps({**report, **GUARDS}, indent=2))
    return 0 if success and reason is None else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    elif not sys.argv[1:]:
        raise SystemExit(supervise())
    else:
        raise SystemExit('No configurable inputs: this diagnostic is pinned to run 76.')
