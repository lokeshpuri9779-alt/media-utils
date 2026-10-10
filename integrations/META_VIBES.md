# Meta AI / Vibes handoff

This optional adapter prepares scene prompts and validates exported MP4 clips.
It does **not** claim to generate Meta videos through an official API.
It does not modify ASTRA's current upload schedule, credentials, or CI.

Create a JSON manifest:
```json
{"scenes":[{"prompt":"Animate the reference image: the boy approaches a glowing machine."},{"prompt":"The boy inserts his last coin into the machine."}]}
```

Prepare prompts:
```sh
python integrations/meta_vibes_handoff.py prepare --manifest story.json
```

Use the prompts in Meta AI/Vibes and export resulting clips as
`meta_handoff/clips/scene_001.mp4`, `scene_002.mp4`, etc.

Check completeness:
```sh
python integrations/meta_vibes_handoff.py check --manifest story.json
```

Only pass clips to ASTRA's existing assembler after the check returns
`"ready": true`. An actual assembly/publishing integration requires
verification of the existing pipeline entry points and media quality checks.

Do not use unofficial session-cookie APIs or bypass generation limits.
