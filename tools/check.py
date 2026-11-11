#!/usr/bin/env python3
"""Lint the built site against the content rules and privacy requirements.

Usage: check.py dist [--strict]

Errors always fail. Warnings fail only with --strict. Notes never fail.
Rules (see Website_Implementation_Plan §12):
  forbidden phrases · numbers with units outside approved blocks · external link
  allow-list (data-allow="units" exempts a block) · robots/no-index · no third-party scripts, styles or fonts · asset
  budgets · alt text · autoplay hygiene · heading order · copy length · flags off
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = [
    r"\boutperform", r"\bcoming soon\b", r"\bto be published\b", r"\bunder review\b",
    r"\bpreprint\b", r"\bour paper\b", r"\bgithub\.com\b", r"\bgitlab\b", r"\bsource code\b",
    r"\brepositor(y|ies)\b", r"\.py\b", r"\.cpp\b", r"\.yaml\b", r"\blaunch file\b",
    r"\bparameter(s)?\b", r"\bstate[- ]of[- ]the[- ]art\b", r"\bbeats?\b",
]
ALLOWED_SENTENCE = re.compile(r"detailed methodology and code are not shared at this stage", re.I)
UNITS = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:m/s²|m/s\^2|m/s|Hz|ms|kg|cm|mm|%|fps)\b")
RESULT_NUMBERS = re.compile(r"\b(?:22\.\d\d|25\.37|17\.02|4\.58|7\.10|5\.6[12]|123\.9\d|115\.90|113\.62|5\.58|5\.07|5\.03|4\.80|5\.25|4\.72)\b")

ALLOWED_HOSTS = {
    "arxiv.org", "www.youtube-nocookie.com", "www.youtube.com", "youtu.be",
    "linkedin.com", "www.linkedin.com", "okanarif.github.io", "tum.de", "www.tum.de", "www.asg.ed.tum.de",
}
BUDGETS_MB = {"assets/video/hero.mp4": 15, "assets/video/sim.mp4": 12, "assets/video/flights.mp4": 50}
IMAGE_MAX_KB = 600
TOTAL_MAX_MB = 120
PRIVATE_PATH_MARKERS = ("Media/", "Planning_Documents/")


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.blocks: list[tuple[str, str, dict]] = []  # (tag, text, attrs) for p/li/figcaption
        self.links: list[dict] = []
        self.imgs: list[dict] = []
        self.videos: list[dict] = []
        self.scripts: list[dict] = []
        self.linktags: list[dict] = []
        self.metas: list[dict] = []
        self.iframes: list[dict] = []
        self.headings: list[tuple[int, str]] = []
        self.flagged: list[str] = []
        self._stack: list[tuple[str, list[str], dict]] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-flag" in a:
            self.flagged.append(a["data-flag"])
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "a": self.links.append(a)
        elif tag == "img": self.imgs.append(a)
        elif tag == "video": self.videos.append(a)
        elif tag == "script": self.scripts.append(a)
        elif tag == "link": self.linktags.append(a)
        elif tag == "meta": self.metas.append(a)
        elif tag == "iframe": self.iframes.append(a)
        if tag in ("p", "li", "figcaption", "h1", "h2", "h3", "h4", "td", "th", "dd"):
            self._stack.append((tag, [], a))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)
        if self._stack and self._stack[-1][0] == tag:
            t, parts, a = self._stack.pop()
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            if t in ("h1", "h2", "h3", "h4"):
                self.headings.append((int(t[1]), text))
            elif text:
                self.blocks.append((t, text, a))

    def handle_data(self, data):
        if self._skip:
            return
        self.text.append(data)
        for _, parts, _ in self._stack:
            parts.append(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    args = ap.parse_args()
    dist: Path = args.dist
    errors, warnings, notes = [], [], []

    html_files = sorted(dist.rglob("*.html"))
    if not html_files:
        print("[check] ERROR: no HTML in dist", file=sys.stderr)
        return 1
    flags = yaml.safe_load((ROOT / "content" / "flags.yaml").read_text())
    on_flags = {k for k, v in flags.items() if v}

    for page_path in html_files:
        raw = page_path.read_text(encoding="utf-8")
        page = Page(); page.feed(raw)
        rel = page_path.relative_to(dist)
        text = re.sub(r"\s+", " ", " ".join(page.text))
        text_for_rules = ALLOWED_SENTENCE.sub("", text)

        # 1. forbidden phrases
        for pat in FORBIDDEN:
            for m in re.finditer(pat, text_for_rules, re.I):
                ctx = text_for_rules[max(0, m.start() - 40): m.end() + 40]
                errors.append(f"{rel}: forbidden phrase '{m.group(0)}' … {ctx!r}")

        # 2. numbers with units / known result numbers
        allowed_numbers = "show_flight_numbers" in on_flags
        for tag, block, attrs in page.blocks:
            if attrs.get("data-flag") == "show_flight_numbers" and allowed_numbers:
                continue
            if attrs.get("data-allow") == "units":   # simulation dynamic limits, deliberate
                continue
            for m in UNITS.finditer(block):
                errors.append(f"{rel}: quantity with unit '{m.group(0)}' in <{tag}>: {block[:80]!r}")
            for m in RESULT_NUMBERS.finditer(block):
                errors.append(f"{rel}: result-table number '{m.group(0)}' in <{tag}>: {block[:80]!r}")

        # 3. external links
        for a in page.links:
            href = a.get("href", "")
            if href.startswith(("http://", "https://")):
                host = urlparse(href).hostname or ""
                if host not in ALLOWED_HOSTS:
                    errors.append(f"{rel}: external link to non-allow-listed host {host} ({href})")
                if "noopener" not in a.get("rel", ""):
                    warnings.append(f"{rel}: external link without rel=noopener ({href})")
            elif href.startswith("http:"):
                errors.append(f"{rel}: insecure link {href}")

        # 4. privacy / visibility
        robots = [m for m in page.metas if m.get("name") == "robots"]
        if not robots or "noindex" not in robots[0].get("content", ""):
            errors.append(f"{rel}: missing <meta name=robots content=noindex>")
        for s in page.scripts:
            src = s.get("src", "")
            if src.startswith(("http://", "https://", "//")):
                errors.append(f"{rel}: third-party script {src}")
        for l in page.linktags:
            href = l.get("href", "")
            if href.startswith(("http://", "https://", "//")):
                errors.append(f"{rel}: third-party stylesheet/font {href}")
        if "fonts.googleapis.com" in raw or "fonts.gstatic.com" in raw:
            errors.append(f"{rel}: Google Fonts reference")
        for marker in PRIVATE_PATH_MARKERS:
            if marker in raw:
                errors.append(f"{rel}: references private path containing '{marker}'")

        # 5. assets referenced exist
        refs = set(re.findall(r'(?:src|href|srcset|poster)="(assets/[^"\s]+)"', raw))
        refs |= set(re.findall(r'url\((assets/[^)]+)\)', raw))
        for ref in sorted(refs):
            if not (dist / ref).exists():
                errors.append(f"{rel}: referenced asset missing {ref}")

        # 6. accessibility basics
        for img in page.imgs:
            if "alt" not in img:
                errors.append(f"{rel}: <img> without alt ({img.get('src')})")
        for v in page.videos:
            if "autoplay" in v and ("muted" not in v or "playsinline" not in v):
                errors.append(f"{rel}: autoplay video must be muted + playsinline ({v.get('poster')})")
            if "poster" not in v:
                warnings.append(f"{rel}: video without poster")
        for f in page.iframes:
            if not f.get("title"):
                errors.append(f"{rel}: iframe without title")
        last = 0
        for level, title in page.headings:
            if level > last + 1:
                warnings.append(f"{rel}: heading jumps h{last} -> h{level} at {title!r}")
            last = level
        if sum(1 for l, _ in page.headings if l == 1) != 1:
            errors.append(f"{rel}: expected exactly one <h1>")

        # 7. copy length (plan: 2-3 sentences, one media per block)
        for tag, block, _ in page.blocks:
            words = len(block.split())
            if tag == "p" and words > 60:
                warnings.append(f"{rel}: paragraph longer than 60 words ({words}): {block[:60]!r}")

        # 8. flags off => no gated elements
        for fl in page.flagged:
            if fl not in on_flags:
                errors.append(f"{rel}: element with data-flag={fl} rendered while the flag is off")

        if 'data-youtube=""' in raw:
            notes.append(f"{rel}: YouTube id not set yet (facade shows the poster only)")

    # 9. budgets
    total = 0
    for p in dist.rglob("*"):
        if not p.is_file():
            continue
        size = p.stat().st_size
        total += size
        rel = str(p.relative_to(dist))
        if rel in BUDGETS_MB and size > BUDGETS_MB[rel] * 1_000_000:
            errors.append(f"{rel}: {size / 1e6:.1f} MB exceeds budget {BUDGETS_MB[rel]} MB")
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and size > IMAGE_MAX_KB * 1024:
            warnings.append(f"{rel}: image {size // 1024} KB > {IMAGE_MAX_KB} KB")
        if p.suffix.lower() in (".jpg", ".jpeg"):
            data = p.read_bytes()[:65536]
            if b"Exif\x00\x00" in data:
                errors.append(f"{rel}: JPEG carries EXIF metadata")
    if total > TOTAL_MAX_MB * 1_000_000:
        errors.append(f"dist total {total / 1e6:.0f} MB exceeds {TOTAL_MAX_MB} MB")
    if not (dist / "robots.txt").exists() or "Disallow: /" not in (dist / "robots.txt").read_text():
        errors.append("robots.txt missing or does not disallow all")
    if list(dist.glob("sitemap*")):
        errors.append("sitemap present; the site must not be indexed")

    for n in notes: print(f"[check] note: {n}")
    for w in warnings: print(f"[check] WARNING: {w}")
    for e in errors: print(f"[check] ERROR: {e}", file=sys.stderr)
    failed = bool(errors) or (args.strict and bool(warnings))
    print(f"[check] {len(errors)} errors, {len(warnings)} warnings, {len(notes)} notes, total {total / 1e6:.1f} MB -> {'FAIL' if failed else 'OK'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
