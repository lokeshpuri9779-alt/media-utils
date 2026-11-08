"""One matched, review-only image: FP32 denoiser and original OpenVINO decoder."""
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
from types import SimpleNamespace

import numpy as np

from tools.experimental_cpu_runtime_probe import collect
from tools.experimental_sdxl_decode_review import (
    GUARDS, OV_MODEL, OV_REVISION, REFERENCE_MODEL, REFERENCE_REVISION,
    download_one, run_bounded_worker, sha256, validate_latents,
)
from tools.experimental_sdxl_denoiser_review import (
    WEIGHT_FILE, WEIGHT_BYTES, WEIGHT_SHA, CONFIG_SHA, screen, validate_configs, predict_rows,
)
from tools.experimental_sdxl_first_prediction import FILES, PACKS
from tools.experimental_sdxl_load import GIB, available_memory, ONE_IMAGE_PROMPT, ONE_IMAGE_NEGATIVE_PROMPT
from tools.experimental_sdxl_reference_image import INITIAL_SHA, SAMPLE_SHA, load_inputs
from tools.experimental_sdxl_text_review import OV_CONFIG

OUT = Path('artifacts/experimental-openvino/sdxl-fp32-image')
FIRST = Path('artifacts/experimental-openvino/sdxl-fp32-source/fp32-prediction.npy')
FIRST_SHA = '680a029b59f316947d38d5df026f3d07790bb24be0ab424c2b403ed9fe178c7c'
DECODER_FILES = {
    'vae_decoder/config.json': (931, 'd93c03a11ecbd4ecb37c9091e99575ca1b4c8c6302f027024c5570c58cd1f793'),
    'vae_decoder/openvino_model.bin': (49647853, '677a7bd03e9b3f2c113722b3c69672815075531981fa77dd6b36b7a3d3d3e389'),
    'vae_decoder/openvino_model.xml': (324517, '4a14a4b656374a76f5f7ed4cce78d321b34e6c7cba76dbe233e87de568e5330a'),
}
SCALE = 0.13025


def save(name, fields):
    temporary = OUT / (name + '.tmp')
    temporary.write_text(json.dumps({**fields, **GUARDS}, indent=2, allow_nan=False) + '\n')
    temporary.replace(OUT / name)


def sources():
    pack, _, initial = load_inputs()
    if sha256(FIRST) != FIRST_SHA:
        raise ValueError('Run-81 FP32 prediction hash mismatch')
    first = np.load(FIRST, allow_pickle=False)
    if first.shape != (2,4,128,128) or first.dtype != np.float32 or not np.isfinite(first).all():
        raise ValueError('Invalid run-81 prediction')
    return pack, initial, first


def denoise(model, scheduler, pack, initial, first, torch, record, clock=time.monotonic):
    if [float(t) for t in scheduler.timesteps] != list(range(951, 0, -50)):
        raise ValueError('Unexpected 20-step schedule')
    latents = torch.from_numpy(initial.copy())  # Already scaled by the original initial sigma.
    started = clock()
    intervals, times, timesteps = [], {}, []
    live_calls = 0
    for index, timestep in enumerate(scheduler.timesteps):
        step_started = clock()
        sample = scheduler.scale_model_input(torch.cat([latents, latents]), timestep)
        if index == 0:
            if hashlib.sha256(sample.detach().cpu().numpy().tobytes()).hexdigest() != SAMPLE_SHA:
                raise ValueError('Cached FP32 prediction input mismatch')
            prediction = first.copy()
        else:
            def on_row(label, value, seconds):
                nonlocal live_calls
                live_calls += 1
                times[f'{index}:{label}'] = seconds
            prediction = predict_rows(model, sample, timestep, pack, torch, on_row)
        tensor = torch.from_numpy(prediction)
        negative, positive = tensor[0:1], tensor[1:2]
        guided = negative + 7.5 * (positive - negative)
        latents = scheduler.step(guided, timestep, latents, return_dict=False)[0]
        validate_latents(latents.detach().cpu().numpy())
        intervals.append(clock() - step_started)
        timesteps.append(float(timestep))
        state = {'completed_scheduler_updates': len(timesteps), 'timesteps': timesteps.copy(),
                 'cached_predictions_used': 1, 'live_forward_calls': live_calls,
                 'call_seconds': times.copy(), 'step_seconds': intervals.copy(),
                 'elapsed_seconds': clock() - started}
        record('trajectory.json', state)
        print(f'Completed scheduler step {index + 1}/20; live FP32 calls {live_calls}/38', flush=True)
        if index == 2:
            projected = clock() - started + 17 * max(intervals[1:3]) + 180
            record('inference-budget.json', {'projected_inference_and_decode_seconds': projected,
                'inference_limit_seconds': 2400, 'decoder_reserve_seconds': 180})
            if projected > 2400:
                raise RuntimeError('inference_budget_exceeded')
    if live_calls != 38 or len(timesteps) != 20:
        raise ValueError('Incomplete FP32 trajectory')
    return latents.detach().cpu().numpy().copy()


def original_decode(root, array, torch):
    """Use the pinned original decoder, scale exactly once and postprocess normally."""
    validate_latents(array)
    import openvino as ov
    from diffusers.image_processor import VaeImageProcessor
    from optimum.intel.openvino.modeling_diffusion import OVModelVaeDecoder, OVDiffusionPipeline
    config = json.loads((root / 'export/vae_decoder/config.json').read_text())
    if config.get('scaling_factor') != SCALE or config.get('latent_channels') != 4:
        raise ValueError('Original decoder configuration mismatch')
    host = SimpleNamespace(_compile_only=False, _device='CPU', device=torch.device('cpu'),
        ov_config=OV_CONFIG.copy(), model_save_dir=root / 'export', vae_scale_factor=8)
    graph = ov.Core().read_model(root / 'export/vae_decoder/openvino_model.xml')
    host.vae_decoder = OVModelVaeDecoder(graph, host, 'vae_decoder')
    host.vae_decoder.model = OVDiffusionPipeline._reshape_vae_decoder(
        host, graph, height=1024, width=1024, num_images_per_prompt=1)
    host.vae_decoder.compile()
    with torch.inference_mode():
        pixels = host.vae_decoder(torch.from_numpy(array.copy()) / SCALE, return_dict=False)[0]
    if tuple(pixels.shape) != (1,3,1024,1024) or not torch.isfinite(pixels).all().item():
        raise ValueError('Invalid decoder pixels')
    image = VaeImageProcessor(vae_scale_factor=8).postprocess(pixels, output_type='pil')[0]
    if image.size != (1024,1024) or image.mode != 'RGB':
        raise ValueError('Unexpected decoded image format')
    return image


def worker():
    save('stage.json', {'stage':'validate'})
    pack, initial, first = sources()
    import psutil
    import torch
    from diffusers import EulerDiscreteScheduler, UNet2DConditionModel
    from safetensors.torch import load_file
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    with tempfile.TemporaryDirectory(prefix='astra-fp32-image-') as directory:
        root = Path(directory)
        preflight = screen(psutil.Process().memory_info().rss, available_memory(),
                           shutil.disk_usage(root).free - sum(n for n,_ in DECODER_FILES.values()))
        preflight['decoder_disk_reserve_bytes'] = sum(n for n,_ in DECODER_FILES.values())
        save('preflight.json', preflight)
        if preflight['reasons']:
            raise RuntimeError('blocked_before_weight_download')
        save('stage.json', {'stage':'download'})
        files = [(OV_MODEL, OV_REVISION, n, 'export/' + n, *FILES[n])
                 for n in ('unet/config.json','scheduler/scheduler_config.json')]
        files.extend((OV_MODEL, OV_REVISION, n, 'export/' + n, *v) for n,v in DECODER_FILES.items())
        files.extend([(REFERENCE_MODEL, REFERENCE_REVISION, 'unet/config.json',
                       'reference/unet/config.json', 1680, CONFIG_SHA),
                      (REFERENCE_MODEL, REFERENCE_REVISION, WEIGHT_FILE, 'reference/' + WEIGHT_FILE,
                       WEIGHT_BYTES, WEIGHT_SHA)])
        manifest = [download_one(item, root=root) for item in files]
        reference = json.loads((root / 'reference/unet/config.json').read_text())
        validate_configs(json.loads((root / 'export/unet/config.json').read_text()), reference)
        save('manifest.json', {'files':manifest, 'source_runs':{'text':'42192924660','initial':'42232753910','first':'42456614547'},
             'source_hashes':{'text_pack':PACKS['reference'],'initial':INITIAL_SHA,'first_prediction':FIRST_SHA}})
        save('request.json', {'seed':42,'steps':20,'guidance_scale':7.5,'width':1024,'height':1024,
            'prompt':ONE_IMAGE_PROMPT,'negative_prompt':ONE_IMAGE_NEGATIVE_PROMPT,
            'denoiser_model':REFERENCE_MODEL,'denoiser_revision':REFERENCE_REVISION,
            'decoder_model':OV_MODEL,'decoder_revision':OV_REVISION})
        save('stage.json', {'stage':'load'})
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        scheduler = EulerDiscreteScheduler.from_pretrained(root / 'export/scheduler',local_files_only=True)
        scheduler.set_timesteps(20,device='cpu')
        if scheduler.config.prediction_type != 'epsilon':
            raise ValueError('Unexpected scheduler prediction type')
        save('scheduler.json', {'class':type(scheduler).__name__,'config':dict(scheduler.config),
             'timesteps':scheduler.timesteps.tolist(),'sigmas':scheduler.sigmas.tolist()})
        with torch.device('meta'):
            model = UNet2DConditionModel.from_config(reference)
        weights = load_file(root / 'reference' / WEIGHT_FILE,device='cpu')
        if any(t.dtype != torch.float32 for t in weights.values()):
            raise ValueError('Reference weights are not FP32')
        model.load_state_dict(weights,strict=True,assign=True)
        del weights
        model.eval().requires_grad_(False)
        model.set_attention_slice('max')
        if any(p.device.type != 'cpu' or (p.is_floating_point() and p.dtype != torch.float32)
               for p in list(model.parameters()) + list(model.buffers())):
            raise ValueError('Non-CPU or non-FP32 model tensor')
        save('runtime.json', {**collect(),'device':'cpu','dtype':'float32','row_batch_size':1,'attention_slice':'max',
            'threads':torch.get_num_threads(),'ov_config':OV_CONFIG,
            'packages':{p:importlib.metadata.version(p) for p in
                        ('torch','diffusers','safetensors','numpy','openvino','optimum-intel','pillow','psutil')}})
        save('stage.json', {'stage':'inference'})
        with torch.inference_mode():
            array = denoise(model,scheduler,pack,initial,first,torch,save)
        np.save(OUT / 'denoised-latents.npy',array,allow_pickle=False)
        save('denoised-latents.json', {'steps_completed':20,'shape':list(array.shape),'dtype':str(array.dtype),
            'scaling':'raw_scheduler_output_unscaled','sha256':sha256(OUT / 'denoised-latents.npy'),
            'run_id':os.getenv('GITHUB_RUN_ID'),'commit':os.getenv('GITHUB_SHA')})
        before = psutil.Process().memory_info().rss
        del model
        gc.collect()
        save('decode-memory.json', {'denoiser_released':True,'rss_before_bytes':before,
                                    'rss_after_bytes':psutil.Process().memory_info().rss})
        save('stage.json', {'stage':'decode'})
        print('FP32 denoiser released; decoding the saved final latent.',flush=True)
        image = original_decode(root,array,torch)
        image.save(OUT / 'sdxl-fp32-seed-42.png',format='PNG')
        save('image-review.json', {'file':'sdxl-fp32-seed-42.png','sha256':sha256(OUT / 'sdxl-fp32-seed-42.png'),
             'width':1024,'height':1024,'images_generated':1,'seed':42,'steps':20,
             'prompt':ONE_IMAGE_PROMPT,'negative_prompt':ONE_IMAGE_NEGATIVE_PROMPT})
        save('worker-result.json', {'status':'image_generated_review_only','images_generated':1})


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    info = {'run_id':os.getenv('GITHUB_RUN_ID'),'commit':os.getenv('GITHUB_SHA'),
        'mode':'fp32_denoiser_matched_image','images_generated':0,
        'limits':{'rss_bytes':12*GIB,'available_ram_floor_bytes':2*GIB,'load_seconds':600,
                  'inference_and_decode_seconds':2400,'overall_seconds':2700}}
    save('report.json',{**info,'status':'started'})
    code,reason,elapsed,peaks = run_bounded_worker(OUT,'tools.experimental_sdxl_fp32_image','inference',slow_review=True)
    done = code == 0 and reason is None and (OUT / 'worker-result.json').exists() and (OUT / 'sdxl-fp32-seed-42.png').exists()
    save('report.json',{**info,'status':reason or ('image_generated_review_only' if done else 'worker_failed'),
        'elapsed_seconds':elapsed,'worker_exit_code':code,'peak_rss_bytes_by_stage':peaks,'images_generated':int(done)})
    if not done:
        print((OUT / 'worker.log').read_text()[-3000:],file=sys.stderr)
    return 0 if done else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    elif not sys.argv[1:]:
        raise SystemExit(main())
    else:
        raise SystemExit('Fixed single-image review only.')
