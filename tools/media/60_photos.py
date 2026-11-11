#!/usr/bin/env python3
"""Drone photos for the web: crop, resize, strip EXIF (phone photos carry GPS),
export JPEG + WebP, record dimensions in assets/manifest.json.

Crops are given as fractions of the source (left, top, right, bottom) so they
survive a re-export of the originals.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Media"
OUT = ROOT / "assets" / "img" / "photos"
MANIFEST = ROOT / "assets" / "manifest.json"

PHOTOS = {
    # stem: (source, crop box as fractions, max width)
    # both crops share the same aspect ratio so the two photos sit side by side at equal size
    "drone-main": ("Figures/Drone_Front_View.jpeg", (0.02, 0.33, 0.98, 0.81), 1600),
    "drone-detail": ("Figures/Drone_Side_View.jpeg", (0.03, 0.44, 0.97, 0.91), 1600),
    # defense photos are shown small on purpose; keep the exports modest
    "defense-solo": ("Photos/Presentation_Photo.jpeg", (0.0, 0.0, 1.0, 1.0), 960),
    "defense-group": ("Photos/Photo_with_Supervisors.jpeg", (0.0, 0.0, 1.0, 1.0), 800),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for stem, (src, (l, t, r, b), width) in PHOTOS.items():
        im = ImageOps.exif_transpose(Image.open(SRC / src))  # apply rotation, then drop EXIF
        W, H = im.size
        im = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
        im = im.convert("RGB")
        clean = Image.new("RGB", im.size)
        clean.putdata(list(im.getdata()))  # new image object: no EXIF, no ICC surprises
        jpg, webp = OUT / f"{stem}.jpg", OUT / f"{stem}.webp"
        clean.save(jpg, quality=85, optimize=True, progressive=True)
        clean.save(webp, quality=82, method=6)
        info = {"width": clean.width, "height": clean.height,
                "jpg_kb": jpg.stat().st_size // 1024, "webp_kb": webp.stat().st_size // 1024}
        manifest[f"assets/img/photos/{stem}.jpg"] = info
        print(f"[photos] {stem:14s} {(W, H)} -> {info}")
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
