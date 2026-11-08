"""Bounded FP32 source-denoiser probe against archived INT8 predictions; no images."""
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np

from tools.experimental_cpu_runtime_probe import collect
from tools.experimental_sdxl_decode_review import (
    GUARDS, OV_MODEL, OV_REVISION, REFERENCE_MODEL, REFERENCE_REVISION,
    download_one, run_bounded_worker, sha256,
)
from tools.experimental_sdxl_first_prediction import FILES, PACKS, branches
from tools.experimental_sdxl_load import GIB, available_memory
from tools.experimental_sdxl_reference_image import (
    INITIAL_SHA, PREDICTION_SHA, SAMPLE_SHA, load_inputs,
)
from tools.experimental_sdxl_text_review import metrics

OUT = Path('artifacts/experimental-openvino/sdxl-denoiser-review')
WEIGHT_FILE = 'unet/diffusion_pytorch_model.safetensors'
WEIGHT_BYTES = 10270077736
WEIGHT_SHA = '357650fbfb3c7b4d94c1f5fd7664da819ad1ff5a839430484b4ec422d03f710a'
CONFIG_SHA = '30ebc70750223e59006f7f2b4e1e6c102570aa19a9c4ae3e1fbe7591332dbae6'
RSS_CAP = 12 * GIB
RAM_FLOOR = 2 * GIB
# Screening allowance for one-row, one-head-at-a-time attention, not a peak guarantee.
WORKSPACE_RESERVE = GIB


def save(name, fields):
    path = OUT / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({**fields, **GUARDS, 'images_generated': 0, 'scheduler_updates': 0},
                              indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def screen(rss, available, disk):
    required_rss = rss + WEIGHT_BYTES + WORKSPACE_RESERVE
    required_available = WEIGHT_BYTES + WORKSPACE_RESERVE + RAM_FLOOR
    required_disk = WEIGHT_BYTES + 2 * GIB
    reasons = []
    if required_rss > RSS_CAP:
        reasons.append('insufficient_rss_headroom')
    if available < required_available:
        reasons.append('insufficient_available_ram')
    if disk < required_disk:
        reasons.append('insufficient_disk')
    return {'status': 'blocked_before_weight_download' if reasons else 'eligible_for_bounded_attempt',
            'reasons': reasons, 'baseline_rss_bytes': rss, 'available_ram_bytes': available,
            'disk_free_bytes': disk, 'weight_file_bytes': WEIGHT_BYTES,
            'workspace_reserve_bytes': WORKSPACE_RESERVE, 'screened_rss_bytes': required_rss,
            'required_available_ram_bytes': required_available, 'required_disk_bytes': required_disk,
            'basis': 'Memory-mapped FP32 weights, measured runtime RSS, 1 GiB workspace allowance; '
                     'sequential conditioning rows and sliced attention. Screening only; runtime limits still apply.'}


def validate_configs(export, reference):
    if not export.get('_name_or_path', '').endswith(f'/snapshots/{REFERENCE_REVISION}/unet'):
        raise ValueError('Export does not identify the pinned source denoiser')
    for key, value in reference.items():
        if not key.startswith('_') and export.get(key) != value:
            raise ValueError(f'Denoiser config mismatch: {key}')
    if reference.get('_class_name') != 'UNet2DConditionModel' or reference.get('sample_size') != 128:
        raise ValueError('Unexpected reference denoiser class or resolution')


def predict_rows(model, sample, timestep, pack, torch, on_row):
    """Keep negative/positive rows independent; never advance the scheduler."""
    outputs = []
    for row, label in enumerate(('negative', 'positive')):
        started = time.monotonic()
        value = model(sample[row:row + 1].clone(), timestep,
                      encoder_hidden_states=torch.from_numpy(pack['sequence'][row:row + 1].copy()),
                      added_cond_kwargs={
                          'text_embeds': torch.from_numpy(pack['pooled'][row:row + 1].copy()),
                          'time_ids': torch.from_numpy(pack['time_ids'][row:row + 1].copy())},
                      return_dict=False)[0].detach().cpu().numpy().copy()
        if value.shape != (1, 4, 128, 128) or value.dtype != np.float32 or not np.isfinite(value).all():
            raise ValueError('Invalid FP32 prediction')
        outputs.append(value)
        on_row(label, value, time.monotonic() - started)
    return np.concatenate(outputs, axis=0)


def worker():
    save('stage.json', {'stage': 'validate'})
    pack, int8_prediction, initial = load_inputs()
    save('progress.json', {'completed_forward_calls': 0})
    # Import the CPU runtime before screening so its resident cost is included.
    import psutil
    import torch
    from diffusers import EulerDiscreteScheduler, UNet2DConditionModel
    from safetensors.torch import load_file

    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    with tempfile.TemporaryDirectory(prefix='astra-fp32-denoiser-') as directory:
        root = Path(directory)
        preflight = screen(psutil.Process().memory_info().rss, available_memory(), shutil.disk_usage(root).free)
        save('preflight.json', preflight)
        if preflight['reasons']:
            save('worker-result.json', {'status': 'blocked_before_weight_download', 'weights_downloaded': False})
            return
        save('stage.json', {'stage': 'download'})
        small_files = [
            (OV_MODEL, OV_REVISION, name, 'export/' + name, *FILES[name])
            for name in ('unet/config.json', 'scheduler/scheduler_config.json')]
        small_files.append((REFERENCE_MODEL, REFERENCE_REVISION, 'unet/config.json',
                            'reference/unet/config.json', 1680, CONFIG_SHA))
        downloaded = [download_one(item, root=root) for item in small_files]
        export = json.loads((root / 'export/unet/config.json').read_text())
        reference = json.loads((root / 'reference/unet/config.json').read_text())
        validate_configs(export, reference)
        downloaded.append(download_one((REFERENCE_MODEL, REFERENCE_REVISION, WEIGHT_FILE,
                                         'reference/' + WEIGHT_FILE, WEIGHT_BYTES, WEIGHT_SHA), root=root))
        save('manifest.json', {'files': downloaded, 'text_run': '42192924660', 'prediction_run': '42232753910',
                               'source_hashes': {'text_pack': PACKS['reference'], 'int8_prediction': PREDICTION_SHA,
                                                 'initial_latent': INITIAL_SHA}})
        save('stage.json', {'stage': 'load'})
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        scheduler = EulerDiscreteScheduler.from_pretrained(root / 'export/scheduler', local_files_only=True)
        scheduler.set_timesteps(20, device='cpu')
        if scheduler.config.prediction_type != 'epsilon' or float(scheduler.timesteps[0]) != 951:
            raise ValueError('Unexpected scheduler')
        sample = scheduler.scale_model_input(torch.from_numpy(np.repeat(initial, 2, axis=0)), scheduler.timesteps[0])
        if hashlib.sha256(sample.numpy().tobytes()).hexdigest() != SAMPLE_SHA:
            raise ValueError('First model input differs from archived run 79')
        np.save(OUT / 'model-input.npy', sample.numpy(), allow_pickle=False)
        np.save(OUT / 'int8-prediction.npy', int8_prediction, allow_pickle=False)
        # Construct only metadata, then assign safetensors-backed CPU tensors without a second weight copy.
        with torch.device('meta'):
            model = UNet2DConditionModel.from_config(reference)
        state = load_file(root / 'reference' / WEIGHT_FILE, device='cpu')
        if any(value.dtype != torch.float32 for value in state.values()):
            raise ValueError('Reference weights are not FP32')
        model.load_state_dict(state, strict=True, assign=True)
        del state
        model.eval().requires_grad_(False)
        model.set_attention_slice('max')
        gc.collect()
        tensors = list(model.parameters()) + list(model.buffers())
        if any(p.device.type != 'cpu' or (p.is_floating_point() and p.dtype != torch.float32) for p in tensors):
            raise ValueError('Reference model contains non-CPU or non-FP32 tensors')
        save('runtime.json', {**collect(), 'device': 'cpu', 'dtype': 'float32', 'row_batch_size': 1,
            'attention_slice': 'max', 'threads': torch.get_num_threads(),
            'parameter_bytes': sum(p.numel() * p.element_size() for p in model.parameters()),
            'packages': {p: importlib.metadata.version(p) for p in ('torch','diffusers','safetensors','numpy','psutil')},
            'loading': 'meta initialization; safetensors CPU tensors; strict load_state_dict(assign=True)',
            'comparison_caveat': 'FP32 PyTorch sliced sequential rows vs archived batched INT8 OpenVINO; '
                                 'differences include backend and execution ordering, not only quantization.'})
        save('control.json', {'sample_sha256': SAMPLE_SHA, 'timestep': 951,
            'sigma': float(scheduler.sigmas[0]), 'guidance_scale': 7.5,
            'ordered_rows': ['negative', 'positive'], 'schedule_length': 20,
            'model': REFERENCE_MODEL, 'revision': REFERENCE_REVISION})
        save('stage.json', {'stage': 'predict'})
        times = {}
        def on_row(label, value, seconds):
            np.save(OUT / f'fp32-{label}.npy', value, allow_pickle=False)
            times[label] = seconds
            save('progress.json', {'completed_forward_calls': len(times), 'call_seconds': times})
        with torch.inference_mode():
            prediction = predict_rows(model, sample, scheduler.timesteps[0], pack, torch, on_row)
        if hashlib.sha256(sample.numpy().tobytes()).hexdigest() != SAMPLE_SHA:
            raise ValueError('Input mutated during reference predictions')
        np.save(OUT / 'fp32-prediction.npy', prediction, allow_pickle=False)
        left, right = branches(int8_prediction), branches(prediction)
        scores = {key: metrics(left[key], right[key]) for key in right}
        sigma = float(scheduler.sigmas[0])
        scores['implied_clean_latent'] = metrics(initial[0] - sigma * left['guided'], initial[0] - sigma * right['guided'])
        save('comparison.json', {'metrics': scores, 'reference_definition': 'Source FP32 PyTorch denoiser',
            'candidate_definition': 'Archived INT8 OpenVINO denoiser with identical reference text inputs',
            'output_sha256': {p.name: sha256(p) for p in OUT.glob('*.npy')},
            'automatic_semantic_threshold': None, 'completed_forward_calls': 2, 'call_seconds': times})
        save('worker-result.json', {'status': 'comparison_complete', 'weights_downloaded': True})


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    info = {'run_id': os.getenv('GITHUB_RUN_ID'), 'commit': os.getenv('GITHUB_SHA'),
        'mode': 'reference_fp32_denoiser_first_step',
        'limits': {'rss_bytes': RSS_CAP, 'available_ram_floor_bytes': RAM_FLOOR,
                   'load_seconds': 600, 'prediction_seconds': 900, 'overall_seconds': 1200}}
    save('report.json', {**info, 'status': 'started'})
    code, reason, elapsed, peaks = run_bounded_worker(OUT, 'tools.experimental_sdxl_denoiser_review', 'predict')
    result = json.loads((OUT / 'worker-result.json').read_text()) if (OUT / 'worker-result.json').exists() else {}
    status = result.get('status')
    done = code == 0 and reason is None and (status == 'blocked_before_weight_download' or
            (status == 'comparison_complete' and (OUT / 'comparison.json').is_file()))
    save('report.json', {**info, 'status': reason or (status if done else 'worker_failed'),
                        'elapsed_seconds': elapsed, 'worker_exit_code': code, 'peak_rss_bytes_by_stage': peaks})
    if not done:
        print((OUT / 'worker.log').read_text()[-3000:], file=sys.stderr)
    return 0 if done else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    elif not sys.argv[1:]:
        raise SystemExit(main())
    else:
        raise SystemExit('Fixed diagnostic only; no image or production options.')
