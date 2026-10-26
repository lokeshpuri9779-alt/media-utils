# Lighthouse weather masking — completed review

Evidence: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40387438514

## Technical evidence
- Reference is the same 512x768 sunset anchor from run 40371027354.
- Storm and aftermath images passed image_quality_report.
- Protected core regions remained exact pixel copies of the source.
- Mean scene differences: storm/anchor 40.34, aftermath/anchor 59.67, storm/after 94.71.
- Scene generation and validation took 1.44 seconds (excluding GitHub Actions setup).
- No diffusion inference, paid API, publication, or automatic approval.

## Actual contact-sheet visual inspection
- The same red lighthouse, lantern, rocks, coastline and framing remain preserved across all three scenes.
- Storm is meaningfully darker with visible rain streaks; aftermath is brighter with a blue sky.
- The storm layer does not produce convincingly rougher wave geometry or physically realistic weather movement.
- Aftermath resembles the sunset composition recolored blue; identical cloud silhouettes are still visible.
- Anchor itself is a short red structure instead of the originally requested tall red-and-white striped lighthouse.
- There is no verified motion/video quality, automatic generalized subject masking, or editorial approval.

## Result
- TECHNICAL_IMAGE_GATE: PASS
- SCENE_DIFFERENTIATION: PASS
- LIGHTHOUSE_STRUCTURAL_CONTINUITY: PASS (for protected regions of this one hard-coded anchor)
- REALISTIC_WEATHER_PHYSICS: NOT MET
- REUSABLE_GENERAL_SEGMENTATION: NOT MET
- PRODUCTION_READY: NO

## Next experiment
Generate a short review-only animated MP4 with modest camera movement,
dynamic rain/cloud overlays, and hold the exact protected lighthouse. Verify
FFmpeg/ffprobe duration, dimensions, frame count and actual frame-to-frame
motion before considering a main ASTRA integration.
