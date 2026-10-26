# OpenVINO anchor-conditioned img2img visual audit

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40373400997

## Verified technical evidence
- Run completed successfully; all two new PNGs pass the technical pixel gate.
- Each at 512x768; NSFW flags false.
- CPU render durations: storm 118.71 s, aftermath 115.62 s.
- Anchor mean absolute RGB difference: storm 17.11, aftermath 16.87.
- Whole job benchmark 348.99 s; peak RSS 13812012 KiB.
- Reused original sunset image from run 40371027354, with img2img strength 0.42 and seed 42.

## Visual inspection of actual contact sheet
- The main red lighthouse, lantern, coastline, and framing remain recognizably consistent, an improvement versus three independent text-to-image samples.
- Both transformed scenes have pronounced coarse, mottled, overprocessed texture, especially in the sky.
- Storm and aftermath are extremely similar in palette, sky pattern, lighting and water. The aftermath fails to deliver a clear blue-sky calm-after-storm change; the storm is insufficiently distinct from it.
- Original anchor's tower is short and solid red, not the original requested tall red-and-white striped lighthouse.

## Decision
- TECHNICAL: PASS
- BASIC_STRUCTURE_CONTINUITY: IMPROVED (manual visual inspection)
- WEATHER_SCENE_DIFFERENTIATION: FAIL
- TEXTURE/IMAGE_AESTHETICS: FAIL
- EXACT_ORIGINAL_LIGHTHOUSE_SPEC: FAIL
- AUTOMATIC_PRODUCTION_APPROVAL: BLOCKED

## Next hypothesis
Keep subject geometry by selectively transforming only the sky and sea; protect tower and rock regions with a mask rather than transforming every pixel. A deterministic PIL sky/ocean transformation provides a cheap CPU baseline before trying heavy inpainting. Use measurable storm-versus-clear contrast checks; require manual visual acceptance and technical quality gate before production integration.
