# ASTRA three-scene CPU storyboard — visual review

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40371027354

## Automated evidence
- All three frames generated at 512 x 768, with pixel-quality checks passing.
- No NSFW flags; the report correctly records `approved: false` and `production_ready: false`.
- The generated contact sheet and individual PNGs remain in the workflow artifact.

## Actual contact-sheet inspection
- Sunset: warm orange sky, sea, recognizable squat red beacon tower.
- Storm: dark clouds and rough waves, similar red beacon but significantly altered construction.
- Aftermath: calmer sea, shorter red hut/tower with a noticeably different lantern, framing and coast.
- The shared red lighthouse motif is present, but the required tall red-and-white *striped* tower was not sustained.
- The same lighthouse's architecture and surroundings do **not** remain consistent from scene to scene.

## Decision
- TECHNICAL_RENDER: PASS (3/3)
- SCENE_CONTRAST: PASS (sunset/storm/clear conditions visually differentiated)
- EXACT_SUBJECT_PROMPT_FIDELITY: FAIL
- SAME_STRUCTURE_CONTINUITY: FAIL
- ANIMATION_VALIDATION: NOT TESTED
- AUTOMATIC_STORY_APPROVAL: BLOCKED

## Next controlled experiment
Use one verified anchor image with image-to-image conditioning or a structural
reference method, instead of three independent text-to-image generations. Measure
identity/structure retention and narrative variation separately. Keep all
pixel-quality, content safety, manual review, and publishing gates unchanged.
