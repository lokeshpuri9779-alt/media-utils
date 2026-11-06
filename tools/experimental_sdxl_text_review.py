"""Trace the run-76 prompt through both SDXL text encoders on CPU."""
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import urllib.request

import numpy as np

from tools.experimental_cpu_runtime_probe import collect
from tools.experimental_sdxl_decode_review import (
    GUARDS, OV_MODEL, OV_REVISION, REFERENCE_MODEL, REFERENCE_REVISION,
    SOURCE_RUN, run_bounded_worker,
)
from tools.experimental_sdxl_load import GIB, ONE_IMAGE_PROMPT, ONE_IMAGE_NEGATIVE_PROMPT

OUT = Path('artifacts/experimental-openvino/sdxl-text-review')
LOCK = json.loads(Path(__file__).with_name('experimental_sdxl_text_lock.json').read_text())
MODELS = {'export': (OV_MODEL, OV_REVISION), 'reference': (REFERENCE_MODEL, REFERENCE_REVISION)}
PROMPTS = {'positive': ONE_IMAGE_PROMPT, 'negative': ONE_IMAGE_NEGATIVE_PROMPT}
ENCODERS = ('text_encoder', 'text_encoder_2')
OV_CONFIG = {'PERFORMANCE_HINT': 'LATENCY', 'INFERENCE_PRECISION_HINT': 'f32', 'NUM_STREAMS': '1'}


def save(name, data):
    tmp = OUT / (name + '.tmp')
    tmp.write_text(json.dumps({**data, **GUARDS, 'images_generated': 0, 'denoising_steps_executed': 0},
                              indent=2, allow_nan=False) + '\n')
    tmp.replace(OUT / name)


def stage(name):
    save('stage.json', {'stage': name})


def download(root):
    total = sum(size for backend in MODELS for size, _ in LOCK[backend].values())
    if shutil.disk_usage(root).free < total + 2 * GIB:
        raise RuntimeError('Insufficient disk for pinned text components')
    records = {}
    for backend, (model, revision) in MODELS.items():
        records[backend] = {}
        for name, (size, expected) in LOCK[backend].items():
            path = root / backend / name
            path.parent.mkdir(exist_ok=True, parents=True)
            digest = hashlib.sha256()
            url = f'https://huggingface.co/{model}/resolve/{revision}/{name}'
            count = 0
            with urllib.request.urlopen(url, timeout=60) as response, path.open('xb') as out:
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > size:
                        raise ValueError(f'Oversized input: {name}')
                    digest.update(block)
                    out.write(block)
            actual = digest.hexdigest()
            if len(expected) == 40 and size < 2 * 1024 * 1024:
                actual = hashlib.sha1(f'blob {size}\0'.encode() + path.read_bytes()).hexdigest()
            if count != size or actual != expected:
                raise ValueError(f'Integrity mismatch: {backend}/{name}')
            records[backend][name] = {'bytes': size, 'sha256': digest.hexdigest()}
    save('manifest.json', {'revisions': MODELS, 'files': records})


def metrics(export, reference):
    export, reference = (np.asarray(x, dtype=np.float64) for x in (export, reference))
    if export.shape != reference.shape or not export.size:
        raise ValueError('Incompatible conditioning tensors')
    if not np.isfinite(export).all() or not np.isfinite(reference).all():
        raise ValueError('Nonfinite conditioning')
    delta = export - reference
    ov_norm, ref_norm = (np.linalg.norm(x.ravel()) for x in (export, reference))
    return {'shape': list(export.shape), 'rmse': float(np.sqrt(np.mean(delta ** 2))),
            'relative_l2': float(np.linalg.norm(delta.ravel()) / ref_norm) if ref_norm else None,
            'cosine': float(np.sum(export * reference) / (ov_norm * ref_norm)) if ov_norm and ref_norm else None,
            'max_abs': float(np.max(np.abs(delta)))}


def verify_packing(sequence, pooled, time_ids, records):
    """Check the observed boundary against the observed, independent encoder outputs."""
    for row, label in enumerate(('negative', 'positive')):
        expected = np.concatenate([records[name, label]['sequence'] for name in ENCODERS], axis=-1)
        np.testing.assert_array_equal(sequence[row:row + 1], expected)
        np.testing.assert_array_equal(pooled[row:row + 1], records['text_encoder_2', label]['pooled'])
    np.testing.assert_array_equal(time_ids, [[1024, 1024, 0, 0, 1024, 1024]] * 2)


def trace(root, backend, previous):
    import torch
    import openvino as ov
    from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline
    from optimum.intel.openvino.modeling_diffusion import OVModelTextEncoder, OVStableDiffusionXLPipeline
    from transformers import CLIPTextModel, CLIPTextModelWithProjection, CLIPTokenizer

    def array(tensor):
        return tensor.detach().cpu().numpy().copy()

    observed = {}
    tokenizers = [CLIPTokenizer.from_pretrained(root / name, local_files_only=True)
                  for name in ('tokenizer', 'tokenizer_2')]

    class SequentialEncoder:
        dtype = torch.float32

        def __init__(self, name, tokenizer):
            self.name, self.tokenizer = name, tokenizer
            self.config = SimpleNamespace(**json.loads((root / name / 'config.json').read_text()))

        def __call__(self, ids, output_hidden_states):
            label = 'negative' if (self.name, 'positive') in observed else 'positive'
            if (self.name, label) in observed or not output_hidden_states:
                raise ValueError('Unexpected encoder invocation')
            name = self.name
            stage('load')
            if backend == 'export':
                host = SimpleNamespace(_compile_only=False, _device='CPU', device=torch.device('cpu'),
                                       ov_config=OV_CONFIG.copy(), model_save_dir=root)
                graph = ov.Core().read_model(root / name / 'openvino_model.xml')
                graph.reshape({port: [1, self.tokenizer.model_max_length] for port in graph.inputs})
                encoder = OVModelTextEncoder(graph, host, name)
                encoder.compile()
                layer_names = encoder.hidden_states_output_names
                main_output = sorted(graph.outputs[0].names)
            else:
                cls = CLIPTextModel if name == 'text_encoder' else CLIPTextModelWithProjection
                encoder, info = cls.from_pretrained(root / name, local_files_only=True,
                    use_safetensors=True, torch_dtype=torch.float32, output_loading_info=True)
                if any(info.get(k) for k in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')):
                    raise ValueError(f'Incomplete reference weights: {name}: {info}')
                encoder.eval()
                layer_names = None
                main_output = None
            stage('encode')
            result = encoder(ids, output_hidden_states=True)
            seq = array(result.hidden_states[-2])
            token_ids = ids[0].tolist()
            end = token_ids.index(self.tokenizer.eos_token_id)
            core_ids = token_ids[:end + 1]
            detail = {'token_ids': token_ids, 'eos_position': end,
                      'content_matches_replay': core_ids == LOCK['expected_ids'][label],
                      'pad_id': self.tokenizer.pad_token_id,
                      'hidden_states': len(result.hidden_states), 'selected_index': len(result.hidden_states) - 2,
                      'selected_output_name': layer_names[-2] if layer_names else None,
                      'hidden_output_names': layer_names, 'first_output': main_output}
            if previous is not None:
                # A different best-matching layer would make an output-order error worth checking.
                target = previous[name, label]['sequence'][:, :end + 1]
                distances = [metrics(target, array(t)[:, :end + 1])['relative_l2'] for t in result.hidden_states]
                detail['nearest_reference_layer'] = min(range(len(distances)), key=lambda i: distances[i])
            record = {'sequence': seq, 'detail': detail}
            if result[0].ndim == 2:
                record['pooled'] = array(result[0])
            observed[name, label] = record
            # Retain only small outputs across calls. Each encoder's weights leave scope here.
            del encoder
            return result

    captured = {}
    config = json.loads((root / 'unet/config.json').read_text())

    class Captured(Exception):
        pass

    class CaptureUNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = SimpleNamespace(**{**config, 'time_cond_proj_dim': config.get('time_cond_proj_dim')})
            self.add_embedding = SimpleNamespace(linear_1=SimpleNamespace(in_features=config['projection_class_embeddings_input_dim']))

        def forward(self, sample, timestep, *, encoder_hidden_states, added_cond_kwargs, **kwargs):
            captured.update(sequence=array(encoder_hidden_states), pooled=array(added_cond_kwargs['text_embeds']),
                            time_ids=array(added_cond_kwargs['time_ids']))
            raise Captured()

    class CapturePipeline(StableDiffusionXLPipeline):
        @property
        def _execution_device(self):
            return torch.device('cpu')

    if backend == 'export':
        CapturePipeline._get_add_time_ids = OVStableDiffusionXLPipeline._get_add_time_ids
    pipe = CapturePipeline(vae=None, unet=CaptureUNet(), tokenizer=tokenizers[0], tokenizer_2=tokenizers[1],
        text_encoder=SequentialEncoder(ENCODERS[0], tokenizers[0]), text_encoder_2=SequentialEncoder(ENCODERS[1], tokenizers[1]),
        scheduler=EulerDiscreteScheduler.from_pretrained(root / 'scheduler', local_files_only=True),
        add_watermarker=False)
    noise = torch.randn((1, 4, 128, 128), generator=torch.Generator(device='cpu').manual_seed(42), dtype=torch.float32)
    if hashlib.sha256(noise.numpy().tobytes()).hexdigest() != '23c72e908d9e3fbe50836a02f09ccde0acfcf28c00dec75b986c49dadf0c115e':
        raise ValueError('Seed-42 noise differs from run 76')
    try:
        with torch.inference_mode():
            pipe(PROMPTS['positive'], negative_prompt=PROMPTS['negative'], height=1024, width=1024,
                 original_size=(1024, 1024), target_size=(1024, 1024), crops_coords_top_left=(0, 0),
                 negative_original_size=(1024, 1024), negative_target_size=(1024, 1024),
                 negative_crops_coords_top_left=(0, 0), guidance_scale=7.5, num_inference_steps=20,
                 latents=noise, output_type='latent')
    except Captured:
        pass
    else:
        raise RuntimeError('Missing denoiser boundary capture')
    verify_packing(**captured, records=observed)
    np.savez_compressed(OUT / f'{backend}-inputs.npz', **captured)
    save(f'{backend}-trace.json', {'prompts': PROMPTS, 'packing_verified': True,
         'components': {f'{name}/{label}': rec['detail'] for (name, label), rec in observed.items()}})
    return observed, captured


def compare(ov, ref, packed_ov, packed_ref):
    results = {}
    for key, left in ov.items():
        right = ref[key]
        eos = right['detail']['eos_position']
        a, b = left['sequence'], right['sequence']
        item = {'padded_ids_equal': left['detail']['token_ids'] == right['detail']['token_ids'],
                'all': metrics(a, b), 'through_eos': metrics(a[:, :eos+1], b[:, :eos+1]),
                'eos': metrics(a[:, eos], b[:, eos]), 'padding': metrics(a[:, eos+1:], b[:, eos+1:])}
        if 'pooled' in right:
            item['pooled'] = metrics(left['pooled'], right['pooled'])
        results['/'.join(key)] = item
    return {'components': results, 'boundary': {k: metrics(packed_ov[k], packed_ref[k]) for k in packed_ref},
            'guidance_difference': {k: metrics(packed_ov[k][1] - packed_ov[k][0], packed_ref[k][1] - packed_ref[k][0])
                                    for k in ('sequence', 'pooled')}}


def worker():
    stage('download')
    with tempfile.TemporaryDirectory(prefix='astra-clip-') as tmp:
        root = Path(tmp)
        download(root)
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        import torch
        torch.set_num_threads(2)
        torch.set_num_interop_threads(2)
        save('runtime.json', {**collect(), 'packages': {p: importlib.metadata.version(p) for p in
             ('torch', 'transformers', 'optimum-intel', 'diffusers', 'openvino', 'numpy')}, 'ov_config': OV_CONFIG})
        ov, packed_ov = trace(root / 'export', 'export', None)
        gc.collect()
        ref, packed_ref = trace(root / 'reference', 'reference', ov)
        save('comparison.json', compare(ov, ref, packed_ov, packed_ref))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    context = {'source_run': SOURCE_RUN, 'run_id': os.getenv('GITHUB_RUN_ID'), 'commit': os.getenv('GITHUB_SHA'),
               'limits': {'rss_bytes': 12 * GIB, 'minimum_available_ram_bytes': 2 * GIB,
                          'load_seconds': 600, 'encoding_seconds': 900, 'overall_seconds': 1200}}
    save('report.json', {**context, 'status': 'started'})
    code, reason, elapsed, peaks = run_bounded_worker(OUT, 'tools.experimental_sdxl_text_review', 'encode')
    completed = code == 0 and reason is None and (OUT / 'comparison.json').is_file()
    save('report.json', {**context, 'worker_exit_code': code, 'elapsed_seconds': elapsed,
         'peak_rss_bytes_by_stage': peaks, 'status': reason or ('comparison_complete' if completed else 'worker_failed')})
    if not completed:
        print((OUT / 'worker.log').read_text()[-3000:], file=sys.stderr)
    return 0 if completed else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']:
        worker()
    elif not sys.argv[1:]:
        raise SystemExit(main())
    else:
        raise SystemExit('Use the fixed run-76 prompt pair only.')
