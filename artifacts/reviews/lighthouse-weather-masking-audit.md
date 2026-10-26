# Lighthouse CPU-only weather masking: run and visual audit

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40387438514
Artifact: astra-lighthouse-weather-masking-40387438514

## Verified automated evidence
- Run success. All three PNG frames and contact sheet uploaded.
- Weather transformation elapsed 1.44 seconds (excludes dependency installation and runner startup).
- Storm: quality PASS; mean brightness 72.17; variance 377.42; mean change from anchor 40.34.
- Aftermath: quality PASS; mean brightness 166.87; variance 906.36; mean change from anchor 59.67.
- Storm vs aftermath mean absolute RGB difference 94.71; clearly distinct conditions.
- Protected interior pixels are bit-identical to the anchor in both scenes.
- No image generation model or paid API used.

## Actual contact sheet inspection
- Strong improvement over img2img in distinct weather: rain/dark storm and bright blue clear aftermath.
- Lighthouse geometry/lantern/foreground rocks remain visually in place.
- Significant **mask halos**, especially around the upper lighthouse and rock boundaries, where protected orange/golden original pixels meet blue/gray weather treatments.
- Rain streaks are visibly synthetic. Storm is still a simple color-shift/rain overlay; sea waves are not physically altered.
- Original anchor is a short solid red lighthouse, not a tall red-white striped tower as first requested.

## Gates
- TECHNICAL: PASS.
- FAST_CPU_FEASIBILITY: PASS.
- DISTINCT_SCENE_CONDITIONS: PASS.
- SUBJECT_GEOMETRY_PRESERVATION: PASS (reference-specific handcrafted mask; not general segmentation).
- VISUAL_BLEND/AESTHETICS: FAIL (halos/seams).
- SEMANTIC_REALISM: NOT VERIFIED.
- ORIGINAL_TALL_STRIPED_LIGHTHOUSE_SPEC: FAIL.
- PRODUCTION_READY: NO; publishing disabled.

## Next
Refine subject mask to follow actual tower edges, with color-aware subject protection and proper alpha matting/feathering. Add a seam-risk gate comparing adjacent pixels across mask boundaries; avoid promising generalized segmentation from handcrafted anchor coordinates.
