"""Run ASTRA Meta video assembly, optional soundtrack/captions, and technical gate.

No publishing or remote API calls. Only emits ready=True after all stages pass.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
try:
    from integrations.meta_assemble import assemble
    from integrations.meta_audio import add_soundtrack
    from integrations.meta_captions import caption
    from integrations.meta_publish_gate import validate
except ModuleNotFoundError:
    from meta_assemble import assemble
    from meta_audio import add_soundtrack
    from meta_captions import caption
    from meta_publish_gate import validate

def run(manifest: Path, clips: Path, output_dir: Path, soundtrack: Path | None = None, srt: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Never leave a stale final.mp4 that a downstream publisher might pick up.
    final = output_dir / "final.mp4"
    if final.exists():
        final.unlink()
    assembled = output_dir / "assembled.mp4"
    assemble(manifest, clips, assembled)
    current = assembled
    if soundtrack is not None:
        mixed = output_dir / "mixed.mp4"
        add_soundtrack(current, soundtrack, mixed)
        current = mixed
    if srt is not None:
        captioned = output_dir / "captioned.mp4"
        caption(current, srt, captioned)
        current = captioned
    if current != final:
        import shutil
        shutil.copy2(current, final)
    result = validate(final, require_audio=True, min_duration=10)
    if not result["ready"]:
        final.unlink(missing_ok=True)
    result["output"] = str(final)
    result["published"] = False
    return result

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--soundtrack", type=Path)
    p.add_argument("--srt", type=Path)
    args = p.parse_args()
    try:
        result = run(args.manifest, args.clips, args.output_dir, args.soundtrack, args.srt)
    except Exception as exc:
        result = {"ready": False, "published": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 1)

if __name__ == "__main__":
    main()
