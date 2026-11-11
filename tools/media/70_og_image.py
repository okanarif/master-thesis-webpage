#!/usr/bin/env python3
"""Social preview image (1200x630) from the hero poster: dark gradient + title.
Run after 10_hero.sh. Reads the title from content/site.yaml.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
POSTER = ROOT / "assets" / "video" / "hero-poster.jpg"
OUT = ROOT / "assets" / "img" / "og" / "og-1200x630.jpg"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
W, H = 1200, 630


def main() -> None:
    site = yaml.safe_load((ROOT / "content" / "site.yaml").read_text())
    im = Image.open(POSTER).convert("RGB")
    # cover-fit the poster into 1200x630
    scale = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    # bottom-heavy dark gradient for legibility
    grad = Image.new("L", (1, H))
    for i in range(H):
        grad.putpixel((0, i), int(255 * min(1.0, max(0.0, (i / H - 0.25) / 0.6)) * 0.88))
    overlay = Image.new("RGB", (W, H), (11, 15, 20))
    im = Image.composite(overlay, im, grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    ft, fs = ImageFont.truetype(FONT_B, 44), ImageFont.truetype(FONT, 26)
    yy = 300
    for line in textwrap.wrap(site["title"], 44):
        d.text((60, yy), line, font=ft, fill=(236, 241, 246)); yy += 54
    yy += 16
    d.text((60, yy), f'{site["author"]["name"]}  ·  Master\'s thesis  ·  {site["affiliation"]["group"]}, TUM',
           font=fs, fill=(170, 182, 194))
    d.text((60, yy + 40), f'Supervised by {site["affiliation"]["supervisor"]}  ·  {site["affiliation"]["pi"]}', font=fs, fill=(170, 182, 194))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, quality=85, optimize=True)
    print(f"[og] {OUT.relative_to(ROOT)} {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
