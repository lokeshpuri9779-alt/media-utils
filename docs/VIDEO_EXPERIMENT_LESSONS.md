# Astra Video Experiment Lessons

This file intentionally preserves lessons only. The WAN/LTX/GPU/ZeroGPU/Agnes
renderer experiments were rolled back from the active codebase.

## Creative quality
- Technical pass gates do not imply a good video.
- Never use scene count, resolution, duration, or sync alone as a publish-quality proxy.
- A Short must feel like one directed audiovisual work, not independent AI clips stitched together.
- Story, dialogue, action, music, SFX, camera movement, transitions, and reaction beats must be designed on one master timeline before rendering.
- Character identity, spatial continuity, screen direction, eyelines, props, lighting, and action momentum must survive every cut.
- More scenes do not automatically create better pacing or more story.
- Reject same-feel/repetitive visual grammar even when aggregate quality scores pass.

## Audio
- Speaker ownership must be explicit; metadata labels must never be spoken.
- Dialogue timing must be measured from generated audio, not guessed from script length.
- SFX must land on visible actions; music must duck under dialogue.
- Audio/video synchronization is a hard requirement, but good sync alone is not creative quality.

## Provider/architecture
- Validate real provider throughput, quotas, concurrency, latency, continuity, and cost before designing the production pipeline around it.
- Free-tier rate limits can make high-scene-count generation impractical even when individual generations work.
- Cache/checkpoint successful expensive generations; never throw away completed work after a later failure.
- Do not increase concurrency blindly after HTTP 429/rate-limit signals.
- Keep paid generation fail-closed unless explicit spend approval exists.

## Release policy
- New rendering architectures stay private until visually reviewed.
- A technically successful upload is still a failed prototype if the finished viewing experience is poor.
- Creative Director/pass gates must include component floors and hard failure conditions, not only an aggregate score.
- Public publishing requires coherent story, pacing, continuity, audio, and visual quality—not merely pipeline success.

## Rollback boundary
Active code was restored to commit:
fe15b962a06bd044867f60ed8ee1f23d6c48ee80

This is the last commit immediately before the WAN 2.6 character-video backend entered the repository.
