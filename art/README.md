# ASTRA generated art assets

ASTRA consumes individual production-ready files, not a composite overview sheet.

- Characters, props, overlays: transparent PNG/WebP with usable alpha, minimum 256×256 source pixels.
- Backgrounds: clean, text-free vertical image, minimum 540×960 pixels.
- Every manifest entry must be approved; paths must stay inside this repository.

Run `python tools/validate_art_assets.py` before rendering. Low-resolution atlas thumbnails, opaque foregrounds, missing files and unsafe paths are rejected.

The current generated composite is a visual catalogue, not individually cropped transparent production assets. Split and quality-check its components before registering them.
