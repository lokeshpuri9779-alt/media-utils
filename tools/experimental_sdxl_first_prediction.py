"""Two first-timestep SDXL predictions with run-78 text inputs. CPU review only."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

import numpy as np
from tools.experimental_cpu_runtime_probe import collect
from tools.experimental_sdxl_decode_review import GUARDS, OV_MODEL, OV_REVISION, download_one, run_bounded_worker, sha256
from tools.experimental_sdxl_load import GIB
from tools.experimental_sdxl_text_review import OV_CONFIG, metrics

OUT = Path('artifacts/experimental-openvino/sdxl-first-prediction')
SOURCE = Path('artifacts/experimental-openvino/sdxl-text-source')
SOURCE_RUN = '42192924660'
PACKS = {
    'export': '7a2162e015cbfeb287f6c79a0f1a59074790750658d85b5242ffadca096c38f0',
    'reference': '451c083783cf31f432505f0dc0c49750ddd00cc1650b9348cf239a15569ff3af',
}
FILES = {
    'scheduler/scheduler_config.json': (676, '042a1410e49afa22f2baefef1ebf7d10bc76decd73345d2edc79bd436091ee3d'),
    'unet/config.json': (1939, 'd042b6f7cfcbc146a99b48b6f5f49826fc71c771cd76baa76d6a5107b2be9d1f'),
    'unet/openvino_model.xml': (6338341, '5d8ab264d7c15e1ef00221fb60711d141ff963a1b4b1b5fbbbc9ee9ad2f3c342'),
    'unet/openvino_model.bin': (2576698520, 'ba78c7fbab3ddfebcb3482fa2df90161deeab537f1615fdd49fd27e842c4271f'),
}
NOISE_SHA = '23c72e908d9e3fbe50836a02f09ccde0acfcf28c00dec75b986c49dadf0c115e'
GUIDANCE = 7.5


def save(name, fields):
    path = OUT / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({**fields, **GUARDS, 'images_generated': 0, 'scheduler_updates': 0},
                              indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def packs_from(source):
    result = {}
    for label, expected in PACKS.items():
        path = source / f'{label}-inputs.npz'
        if sha256(path) != expected:
            raise ValueError(f'Run-78 conditioning hash mismatch: {label}')
        with np.load(path, allow_pickle=False) as data:
            shapes = {'sequence': (2, 77, 2048), 'pooled': (2, 1280), 'time_ids': (2, 6)}
            if set(data.files) != set(shapes):
                raise ValueError('Unexpected conditioning fields')
            result[label] = {key: data[key] for key in shapes}
            for key, shape in shapes.items():
                value = result[label][key]
                if value.dtype != np.float32 or value.shape != shape or not np.isfinite(value).all():
                    raise ValueError(f'Invalid conditioning: {label}/{key}')
        np.testing.assert_array_equal(result[label]['time_ids'], [[1024, 1024, 0, 0, 1024, 1024]] * 2)
    return result


def branches(prediction):
    if prediction.shape[0] != 2 or prediction.dtype != np.float32 or not np.isfinite(prediction).all():
        raise ValueError('Expected two finite float32 prediction rows')
    negative, positive = prediction
    residual = positive - negative
    return {'negative': negative, 'positive': positive, 'prompt_residual': residual,
            'guided': negative + GUIDANCE * residual}


def worker():
    save('stage.json', {'stage': 'validate'})
    packs = packs_from(SOURCE)
    save('progress.json', {'completed_forward_calls': 0})
    with tempfile.TemporaryDirectory(prefix='astra-first-prediction-') as directory:
        root = Path(directory)
        if shutil.disk_usage(root).free < sum(size for size, _ in FILES.values()) + 2 * GIB:
            raise RuntimeError('Insufficient disk for pinned denoiser')
        save('stage.json', {'stage': 'download'})
        files = [download_one((OV_MODEL, OV_REVISION, name, name, size, digest), root=root)
                 for name, (size, digest) in FILES.items()]
        save('manifest.json', {'files': files, 'pack_hashes': PACKS, 'source_run': SOURCE_RUN})
        save('stage.json', {'stage': 'load'})
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        import openvino as ov
        import torch
        from diffusers import EulerDiscreteScheduler
        from optimum.intel.openvino.modeling_diffusion import OVDiffusionPipeline, OVModelUnet

        torch.set_num_threads(2)
        scheduler = EulerDiscreteScheduler.from_pretrained(root / 'scheduler', local_files_only=True)
        scheduler.set_timesteps(20, device='cpu')
        t = scheduler.timesteps[0]
        if scheduler.config.prediction_type != 'epsilon':
            raise ValueError('Unexpected scheduler prediction type')
        noise = torch.randn((1, 4, 128, 128), generator=torch.Generator(device='cpu').manual_seed(42),
                            dtype=torch.float32)
        if hashlib.sha256(noise.numpy().tobytes()).hexdigest() != NOISE_SHA:
            raise ValueError('Initial noise differs from run 76')
        latent = noise * scheduler.init_noise_sigma
        model_input = scheduler.scale_model_input(torch.cat([latent, latent]), t)
        sample_hash = hashlib.sha256(model_input.numpy().tobytes()).hexdigest()
        time_ids = torch.from_numpy(packs['export']['time_ids'].copy())
        host = SimpleNamespace(_compile_only=False, _device='CPU', device=torch.device('cpu'),
            ov_config=OV_CONFIG.copy(), model_save_dir=root, vae_scale_factor=8,
            text_encoder_2=SimpleNamespace(config={'projection_dim': packs['export']['pooled'].shape[-1]}))
        graph = ov.Core().read_model(root / 'unet/openvino_model.xml')
        host.unet = OVModelUnet(graph, host, 'unet')
        host.unet.model = OVDiffusionPipeline._reshape_unet(host, graph, batch_size=1, height=1024, width=1024,
                                                           num_images_per_prompt=1, tokenizer_max_length=77)
        host.unet.compile()
        save('control.json', {'source_run': SOURCE_RUN, 'model': OV_MODEL, 'revision': OV_REVISION,
            'seed': 42, 'noise_sha256': NOISE_SHA, 'sample_sha256': sample_hash, 'input_shape': list(model_input.shape),
            'time_ids': time_ids.tolist(), 'step_index': 0, 'schedule_length': len(scheduler.timesteps),
            'timestep': float(t), 'sigma': float(scheduler.sigmas[0]), 'init_sigma': float(scheduler.init_noise_sigma),
            'guidance_scale': GUIDANCE, 'ordered_rows': ['negative', 'positive'],
            'model_inputs': {port.get_any_name(): str(port.get_partial_shape()) for port in graph.inputs}})
        save('runtime.json', {**collect(), 'ov_config': OV_CONFIG,
            'packages': {p: importlib.metadata.version(p) for p in ('openvino','optimum-intel','torch','diffusers','numpy')}})
        save('stage.json', {'stage': 'predict'})
        outputs, durations = {}, {}
        with torch.inference_mode():
            for label in ('export', 'reference'):
                pack = packs[label]
                start = time.monotonic()
                value = host.unet(model_input, t, encoder_hidden_states=torch.from_numpy(pack['sequence']),
                    added_cond_kwargs={'text_embeds': torch.from_numpy(pack['pooled']), 'time_ids': time_ids},
                    return_dict=False)[0]
                outputs[label] = value.detach().cpu().numpy().copy()
                durations[label] = time.monotonic() - start
                if outputs[label].shape != (2, 4, 128, 128):
                    raise ValueError('Unexpected prediction shape')
                if hashlib.sha256(model_input.numpy().tobytes()).hexdigest() != sample_hash:
                    raise ValueError('Denoiser mutated shared sample')
                np.testing.assert_array_equal(time_ids.numpy(), pack['time_ids'])
                np.save(OUT / f'{label}-prediction.npy', outputs[label], allow_pickle=False)
                save('progress.json', {'completed_forward_calls': len(outputs), 'call_seconds': durations})
        export, ref = (branches(outputs[key]) for key in ('export','reference'))
        scores = {key: metrics(export[key], ref[key]) for key in ref}
        sigma = float(scheduler.sigmas[0])
        scores['implied_clean_latent'] = metrics(latent.numpy()[0] - sigma * export['guided'],
                                                 latent.numpy()[0] - sigma * ref['guided'])
        np.save(OUT / 'initial-latent.npy', latent.numpy(), allow_pickle=False)
        save('comparison.json', {'metrics': scores, 'completed_forward_calls': 2, 'call_seconds': durations,
            'output_sha256': {p.name: sha256(p) for p in OUT.glob('*.npy')},
            'reference_definition': 'Same INT8 OpenVINO U-Net with source FP32 text conditioning.'})


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    info = {'run_id': os.getenv('GITHUB_RUN_ID'), 'commit': os.getenv('GITHUB_SHA'), 'source_run': SOURCE_RUN,
            'limits': {'rss_bytes': 12*GIB, 'available_ram_floor_bytes': 2*GIB, 'load_seconds': 600,
                       'prediction_seconds': 900, 'overall_seconds': 1200}}
    save('report.json', {**info, 'status': 'started'})
    code, reason, elapsed, peaks = run_bounded_worker(OUT, 'tools.experimental_sdxl_first_prediction', 'predict')
    done = code == 0 and reason is None and (OUT / 'comparison.json').is_file()
    save('report.json', {**info, 'status': reason or ('comparison_complete' if done else 'worker_failed'),
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
        raise SystemExit('Use the fixed first-prediction comparison.')
