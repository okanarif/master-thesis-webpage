#!/usr/bin/env python3
"""Export the method figures for the web.

- Removes the legend band baked into the thesis figures (the site renders one
  shared HTML legend instead).
- Optionally keeps a subset of panels (Fig. 3.2 -> panels C and D).
- Writes PNG + WebP at a fixed width and records dimensions in assets/manifest.json.

Panel borders in the thesis figures are dark lines spanning the full width, so a
row whose mean brightness is low across the whole image is a border row. The
legend lives below the last border row.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Media" / "Figures"
OUT = ROOT / "assets" / "img" / "figures"
MAPS_OUT = ROOT / "assets" / "img" / "maps"
MANIFEST = ROOT / "assets" / "manifest.json"
WIDTH = 2400
DARK_ROW = 90  # mean brightness below this = a full-width border row

FIGURES = {
    # web name: (source file, which horizontal band to keep: "all" | "bottom-half" | "none")
    # "none" = no border/legend band; only the white margin is trimmed.
    "perception": ("Perception_and_Mapping.png", "all"),
    "decomposition": ("Decomposition.png", "all"),
    "frontier": ("Frontier_Selection.png", "all"),
    "architecture": ("ACTOR_Modules.png", "none"),
    "planner-sequential": ("SUPER_SANDO_Modules.png", "none"),
    "planner-actor": ("ACTOR_Planner_Module.png", "none"),
}
TRIM_PAD = 0.02  # margin kept around the content after trimming, fraction of the larger side
MAPS = {f"map_{i}": f"Map_{i}_2D.png" for i in range(1, 5)}
MAP_TITLE_BAND = 0.14  # fraction of the map plots' height taken by the generated title line


def border_rows(im: Image.Image) -> list[int]:
    """Indices of rows that are dark across the full width (panel borders)."""
    col = im.convert("L").resize((1, im.height), Image.Resampling.BOX)
    means = list(col.getdata())
    rows = [y for y, m in enumerate(means) if m < DARK_ROW]
    # collapse runs of adjacent rows into one representative
    groups: list[list[int]] = []
    for y in rows:
        if groups and y - groups[-1][-1] <= 2:
            groups[-1].append(y)
        else:
            groups.append([y])
    return [g[0] for g in groups], [g[-1] for g in groups]


def flatten(im: Image.Image) -> Image.Image:
    """Composite transparent figures onto white so RGB export does not turn them black."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        return bg.convert("RGB")
    return im.convert("RGB")


def trim(im: Image.Image) -> Image.Image:
    """Cut the uniform white margin, keep a small padding."""
    from PIL import ImageChops
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not bbox:
        return im
    pad = int(max(im.size) * TRIM_PAD)
    l, t, r, b = bbox
    return im.crop((max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad)))


def crop_band(im: Image.Image, mode: str) -> Image.Image:
    if mode == "none":
        return trim(im)
    starts, ends = border_rows(im)
    if len(starts) < 2:
        print(f"  ! no border rows found, keeping full image", file=sys.stderr)
        return im
    top, bottom = starts[0], ends[-1]
    if mode == "bottom-half":
        # middle border = the one closest to the vertical centre of the panel area
        mid_target = (top + bottom) / 2
        mid = min(starts[1:-1], key=lambda y: abs(y - mid_target)) if len(starts) > 2 else top
        top = mid
    return im.crop((0, top, im.width, bottom + 1))


def export(im: Image.Image, stem: str, out_dir: Path, width: int) -> dict:
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
    im = im.convert("RGB")
    png = out_dir / f"{stem}.png"
    webp = out_dir / f"{stem}.webp"
    im.save(png, optimize=True)
    im.save(webp, quality=82, method=6)
    return {"width": im.width, "height": im.height,
            "png_kb": png.stat().st_size // 1024, "webp_kb": webp.stat().st_size // 1024}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MAPS_OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    for stem, (src, mode) in FIGURES.items():
        im = flatten(Image.open(SRC / src))
        cropped = crop_band(im, mode)
        info = export(cropped, stem, OUT, WIDTH)
        manifest[f"assets/img/figures/{stem}.png"] = info
        print(f"[figures] {stem:14s} {im.size} -> {info}")

    for stem, src in MAPS.items():
        im = Image.open(SRC / src)
        im = im.crop((0, int(im.height * MAP_TITLE_BAND), im.width, im.height))  # drop the plot title line
        info = export(im, stem, MAPS_OUT, 1200)
        manifest[f"assets/img/maps/{stem}.png"] = info
        print(f"[maps]    {stem:14s} {im.size} -> {info}")

    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
