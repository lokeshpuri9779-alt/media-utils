"""Conservative opt-in faster resampling for Studio's small camera zooms.

Default keeps the existing bicubic production behavior. Enabling the fast path
must be accompanied by representative full-MP4 visual QA before deployment.
"""
from __future__ import annotations

import os
from PIL import Image


def camera_resample():
    """Return a deterministic Pillow interpolation mode; no quality gate bypass."""
    return (Image.Resampling.BILINEAR
            if os.environ.get("ASTRA_FAST_CAMERA_RESAMPLE", "0") == "1"
            else Image.Resampling.BICUBIC)
