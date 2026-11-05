# Native SDXL slow review: denoising completed, memory stop before PNG

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41843537162
Tested commit: 3b149ac07cc5beb09b91d3537e3490ac8d19fd3f
Job: 126621054935
Artifact: 13332153305 (astra-sdxl-one-image-41843537162)
Archive SHA-256: 74870863bdff4d2e374ee10209624a2fe61ce03c0c9f9c399bb141d6199641ca
Artifact expires: 2026-11-11 20:01:56 IST.

## Measured outcome

- The explicit slow-review mode ran; the normal-image and timing-probe steps
  were skipped. All 17 offline checks passed in the live job.
- The timing gate continued: intervals 86.448475 / 84.023698 / 84.000332 s,
  elapsed 254.472505 s, projected total 1862.875365 s including the engineering
  180 s decode reserve, below the selected 2400 s limit.
- The progress log reached 20/20 at 27:58 (reported 83.94 s/step).
- The supervisor then killed the worker for rss_limit, exit -9. Peak sampled
  process-tree RSS was 13,016,092,672 bytes (12.122 GiB), exceeding the 12 GiB cap.
  Shared pages may be counted more than once in this measurement.
- Overall worker elapsed: 1746.249797 s (29.10 min), below the 2700 s ceiling.
  Download/load/compile: 18.351606 / 7.518869 / 12.153433 s.
- No PNG, image-review.json, final latent checkpoint or worker-result.json was
  produced. images_generated=0. Artifact upload succeeded.
- CPU: AMD EPYC 7763, four logical/affinity CPUs. UNet: 2 inference threads,
  1 stream, LATENCY, CPU. Torch threads 2/inter-op 4. Effective cgroup quota
  remains unknown despite readable ancestors reporting max 100000.

request.json, manifest.json, scheduler.json, initial-latents.npy and
conditioning.json were byte-identical to run 41838601016. The model, seed,
native resolution, schedule, conditioning and prompt were controlled.

The memory stop happened after the denoising progress completed and before a
PNG was saved. Decoding is the leading explanation from the pinned pipeline's
control flow, but the old stage marker covered all inference, so the exact
failing allocation is not directly measured. This was neither an inference
timeout nor a completed visual-quality test.

## Smallest corrective validation

The pinned Optimum 2.2.0 OVPipelinePart.clear_requests() sets its compiled
request to None while retaining its IR model. Diffusers 0.39.0 calls the final
step callback after the scheduler update and before VAE scaling/decoding.

Source audit:
- https://github.com/huggingface/optimum-intel/blob/v2.2.0/optimum/intel/openvino/modeling_diffusion.py
- https://github.com/huggingface/diffusers/blob/v0.39.0/src/diffusers/pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py

The next isolated change uses only the final (20th) callback to:

1. Save the unscaled final scheduler latent as an atomic NumPy checkpoint plus
   its hash, model/revision, shape, seed, completed steps and unapproved flags.
2. Release compiled requests for UNet, both text encoders and the unused VAE
   encoder, then collect garbage. The VAE decoder and IR models remain intact.
3. Let the existing pipeline perform its unchanged scaling, decode and image
   postprocessing. No tiling, precision, prompt, seed or scheduler change.

The decode stage gets its own memory report and supervisor stage marker. Its
time remains part of the original inference deadline, not a fresh timebox.
The RSS/available-RAM limits and slow-review time limits are unchanged.

Twenty-one offline tests pass, including checkpoint byte preservation, cleanup
only after step 20, leaving the decoder intact, failure propagation with a
retained checkpoint, and timeout enforcement across the decode transition.
The first local test attempt lacked psutil; the tests now mock that monitor
explicitly. Live memory reduction and image quality are not yet established.

Run one controlled slow-review attempt with these changes. If it fails again
after checkpointing, inspect the retained latent and decode-memory reports
before considering a decode-only follow-up; do not blindly repeat denoising or
raise the memory cap. The checkpoint cannot recover the already-finished run
41843537162 because that run did not save final latents.

## Readiness

The current evidence still does not support a reliable free ASTRA image path.
Semantic fidelity and character consistency remain unverified for native SDXL;
earlier lower-resolution images failed visual criteria. A completed single
truck would still need manual review, followed by separate scene/identity
validation. approved=false, production_ready=false, published=false and manual
visual review required remain unchanged. No automatic approval, production
fallback, paid API, publishing or main integration is enabled.
