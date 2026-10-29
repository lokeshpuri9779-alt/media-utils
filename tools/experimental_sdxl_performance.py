"""Bounded SDXL timing probe; deliberately stops before decode."""
import os
import time
from pathlib import Path

PROBE_STEPS = 3

class ProbeComplete(Exception):
    pass

def runtime_details(pipe, torch):
    from tools.experimental_cpu_runtime_probe import collect
    data = collect()
    data['torch_threads'] = torch.get_num_threads()
    data['torch_interop_threads'] = torch.get_num_interop_threads()
    data['unet_effective_properties'] = {}
    for name in ('INFERENCE_NUM_THREADS', 'NUM_STREAMS', 'PERFORMANCE_HINT', 'EXECUTION_DEVICES'):
        try:
            value = pipe.unet.request.get_property(name)
            data['unet_effective_properties'][name] = (
                value if isinstance(value, (int, float, str, bool, list)) else str(value))
        except (RuntimeError, AttributeError, TypeError) as exc:
            data['unet_effective_properties'][name] = {'unavailable': type(exc).__name__}
    # Resolve the process's cgroup v2 path, then inspect its ancestors for limits.
    try:
        membership = Path('/proc/self/cgroup').read_text().strip()
        data['cgroup_membership'] = membership
        relative = next(line.split(':', 2)[2] for line in membership.splitlines()
                        if line.startswith('0::'))
        root = Path('/sys/fs/cgroup').resolve()
        current = (root / relative.lstrip('/')).resolve()
        limits = []
        while current == root or root in current.parents:
            try:
                limits.append({'path': str(current / 'cpu.max'),
                               'value': (current / 'cpu.max').read_text().strip()})
            except OSError:
                pass
            if current == root:
                break
            current = current.parent
        data['cgroup_v2_ancestor_cpu_limits'] = limits
    except (OSError, StopIteration):
        data['cgroup_v2_ancestor_cpu_limits'] = None
    return data

def run_probe(pipe, kwargs, save, clock=time.monotonic):
    report = {'status': 'started', 'schedule_steps': kwargs['num_inference_steps'],
              'stop_after_steps': PROBE_STEPS, 'steps': [], 'images_generated': 0,
              'approved': False, 'production_ready': False, 'published': False,
              'manual_visual_review_required': True}
    started = previous = clock()
    def callback(pipeline, step_index, timestep, callback_kwargs):
        nonlocal previous
        if step_index != len(report['steps']):
            raise RuntimeError('Unexpected callback order')
        now = clock()
        report['steps'].append({'step': step_index + 1,
            'seconds_since_previous_callback': now - previous,
            'elapsed_seconds': now - started,
            'includes_prompt_setup': step_index == 0})
        previous = now
        save('performance.json', report)
        if len(report['steps']) == PROBE_STEPS:
            raise ProbeComplete()
        return callback_kwargs
    save('performance.json', report)
    try:
        pipe(**kwargs, output_type='latent', callback_on_step_end=callback,
             callback_on_step_end_tensor_inputs=[])
    except ProbeComplete:
        if len(report['steps']) != PROBE_STEPS:
            raise RuntimeError('Probe stopped before collecting three steps')
        report['status'] = 'performance_probe_complete'
        save('performance.json', report)
        return
    raise RuntimeError('Pipeline returned without the required early stop')
