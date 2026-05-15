"""Downscale + re-encode HCSO booking photos to honor the 'less MB' constraint.

HCSO embeds 800x1000 JPEGs in inmate-detail HTML (declared as image/png but the
bytes are JPEG). They display at 274px wide on hcso.org itself. JCStream stores a
250x312 JPEG at quality 78 — the same visual size HCSO presents publicly, at
roughly 1/10 the file size of the original.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

DISPLAY_SIZE = (250, 312)
JPEG_QUALITY = 78


def downscale_and_save(raw: bytes, dest: Path) -> bool:
    """Write a downscaled JPEG to ``dest``.

    Returns True on success, False if the bytes can't be decoded as an image.
    """
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            im.thumbnail(DISPLAY_SIZE, Image.Resampling.LANCZOS)
            dest.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except (UnidentifiedImageError, OSError) as e:
        log.warning("failed to decode/save photo to %s: %s", dest, e)
        return False
