"""Complete the original 20-step truck request using archived reference text and step zero."""
from pathlib import Path
import hashlib
import numpy as np

from tools.experimental_sdxl_first_prediction import PACKS, packs_from
from tools.experimental_sdxl_decode_review import GUARDS, sha256

TEXT = Path('artifacts/experimental-openvino/sdxl-text-source')
STEP = Path('artifacts/experimental-openvino/sdxl-prediction-source')
PREDICTION_SHA = '59e67dc59c95f9d4ae20bf17619ce0dcd9c87d304d1da1fa5f66d5fa9b94b5c2'
INITIAL_SHA = 'a466348b963d47a523734dfe815ece75bf8740691c5da8409dd85ae36664974d'
SAMPLE_SHA = 'feaff25c7684b1281f1cba182d9c71494c2f14762b8341ee3ec9daecd9466419'


def load_inputs():
    pack = packs_from(TEXT)['reference']
    arrays = []
    for filename, expected, shape in [('reference-prediction.npy', PREDICTION_SHA, (2, 4, 128, 128)),
                                      ('initial-latent.npy', INITIAL_SHA, (1, 4, 128, 128))]:
        path = STEP / filename
        if sha256(path) != expected:
            raise ValueError(f'Run-79 hash mismatch: {filename}')
        value = np.load(path, allow_pickle=False)
        if value.shape != shape or value.dtype != np.float32 or not np.isfinite(value).all():
            raise ValueError(f'Invalid run-79 tensor: {filename}')
        arrays.append(value)
    return pack, *arrays


def validate_first(sample, timestep, initial, saved_initial, sample_sha=SAMPLE_SHA):
    if float(timestep) != 951 or hashlib.sha256(sample.tobytes()).hexdigest() != sample_sha:
        raise ValueError('Run-79 first timestep or scheduler-scaled input differs')
    np.testing.assert_array_equal(initial, saved_initial)


def render(pipe, sources, save, **kwargs):
    import torch
    pack, first, saved_initial = sources
    sequence, pooled = (torch.from_numpy(pack[k]) for k in ('sequence', 'pooled'))
    original_forward = pipe.unet.forward
    timesteps = []
    live = 0

    def record():
        save('reference-trajectory.json', {**GUARDS, 'text_run': '42192924660', 'prediction_run': '42232753910',
            'text_pack_sha256': PACKS['reference'], 'prediction_sha256': PREDICTION_SHA,
            'initial_sha256': INITIAL_SHA, 'first_scaled_sample_sha256': SAMPLE_SHA,
            'cached_predictions_used': int(bool(timesteps)), 'live_predictions_completed': live,
            'timesteps': timesteps.copy()})

    def forward(sample, timestep, **arguments):
        nonlocal live
        index = len(timesteps)
        if index >= 20 or float(timestep) != float(pipe.scheduler.timesteps[index]):
            raise ValueError('Unexpected timestep sequence')
        # Verify exactly what reaches the denoiser, including negative/positive row order.
        for value, key in ((arguments['encoder_hidden_states'], 'sequence'),
                           (arguments['added_cond_kwargs']['text_embeds'], 'pooled'),
                           (arguments['added_cond_kwargs']['time_ids'], 'time_ids')):
            np.testing.assert_array_equal(value.detach().cpu().numpy(), pack[key])
        if index == 0:
            initial = kwargs['latents'] * pipe.scheduler.init_noise_sigma
            validate_first(sample.detach().cpu().numpy(), timestep, initial.detach().cpu().numpy(), saved_initial)
            result = (torch.from_numpy(first.copy()),)
        else:
            result = original_forward(sample, timestep, **arguments)
            live += 1
        timesteps.append(float(timestep))
        record()
        return result

    record()
    pipe.unet.forward = forward
    try:
        generated = pipe(prompt_embeds=sequence[1:2], negative_prompt_embeds=sequence[0:1],
                         pooled_prompt_embeds=pooled[1:2], negative_pooled_prompt_embeds=pooled[0:1],
                         **kwargs)
    finally:
        pipe.unet.forward = original_forward
    if len(timesteps) != 20 or live != 19:
        raise ValueError('Expected one cached and 19 live predictions')
    return generated
