# Astra Animation Director — Reference Benchmark v1

This profile captures production principles learned from user-approved reference animation.
It does NOT copy characters, plots, frames, proprietary assets, or a studio's signature style.

## Universal target
- Premium stylized 3D animation with original art direction.
- Smooth, intentional character motion; readable silhouettes and strong poses.
- Expressive face, eyes, hands/paws and full-body acting.
- Action -> reaction -> consequence must remain visually causal.
- Cinematic composition: purposeful wide, medium, close/reaction and moving-camera shots.
- Lighting, materials, depth and environmental motion must feel integrated.
- Character identity, proportions, wardrobe, props, geography, lighting and story state persist across cuts.
- Story determines shot count and duration. Never target a fixed number of clips.
- Prefer coherent generated sequences plus editorial coverage over many unrelated generations.
- A technically valid render that feels like stitched AI clips is a failure.

## Short-form bias
Learned from the approved short-form reference:
- Enter the action immediately.
- Favor visual storytelling over exposition.
- Strong pose/action readability on a phone screen.
- Frequent meaningful reactions, not arbitrary cutting.
- Comedy/action timing can be fast, but motion must remain continuous and legible.
- Every cut should advance action, reaction, escalation or payoff.

## Long-form bias
Learned from the approved cinematic short-film reference:
- Organize story as acts/sequences/shots, not a flat clip list.
- Establish geography before complex action.
- Allow emotional holds and quieter beats when story needs them.
- Maintain character/world state over minutes.
- Reuse established locations coherently from new camera positions.
- Track unresolved actions, props, relationships and emotional state into later sequences.
- Use shot variety to serve narrative emphasis rather than constant stimulation.

## Character performance
- Anticipation -> action -> follow-through -> settle.
- Weight, balance and contact should read clearly.
- Secondary motion follows primary motion.
- Eye-lines and reactions must match the source of attention.
- Avoid idle talking-head animation unless dramatically justified.
- Dialogue scenes need speaker ownership and believable performance; if lip sync is weak, stage narration/action/reaction instead of fake mouth flapping.

## Continuity state
Each sequence carries forward:
- character identity and model sheet
- current wardrobe/accessories
- location and spatial layout
- time/weather/lighting
- active props and their positions
- character goals/emotional state
- previous action end-state
- screen direction and eye-lines
- camera/shot transition intent

## Hard rejection conditions
Reject/regenerate when any occurs:
- identity drift or unexplained costume/body changes
- teleporting props/characters or broken geography
- action resets at cuts
- contradictory eye-lines/screen direction
- repetitive camera grammar
- excessive static/slideshow motion
- visibly independent clips with no temporal continuity
- motion artifacts that damage character anatomy
- audio/dialogue/SFX materially out of sync with visible action
- aggregate score passes while a mandatory component floor fails

## Renderer requirements
Rank candidate renderers by:
1. reference/image conditioning
2. temporal and identity consistency
3. video continuation / first-last-frame control
4. character and camera motion quality
5. controllable duration and aspect ratio
6. automation/API/CLI reliability
7. practical compute requirement
8. license/commercial suitability
9. checkpoint/cache/resume support
10. cost, with paid inference disabled unless explicitly approved

OmniRoute is the intelligence/router layer. It does not make a weak renderer acceptable.
