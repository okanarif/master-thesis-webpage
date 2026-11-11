#!/usr/bin/env python3
"""Render the site: content/*.yaml + src/templates -> dist/.

Steps
 1. load content and flags, validate media objects (alt text, referenced assets)
 2. render index.html with Jinja2 (optional keys may be absent; required ones are validated first)
 3. concatenate CSS in cascade order into dist/styles/site.css
 4. copy scripts, static files and assets
 5. print a size report

Asset URLs are relative on purpose: the same build works at / locally and under
/master-thesis-webpage/ on GitHub Pages.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import ChainableUndefined, Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SRC = ROOT / "src"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

MEDIA_TYPES_NEEDING_ALT = {"image", "video_loop", "video_player", "youtube"}


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- content ----
def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise BuildError(f"{path.name}: top level must be a mapping")
    return data


def load_content() -> tuple[dict, dict, dict]:
    site = load_yaml(CONTENT / "site.yaml")
    flags = load_yaml(CONTENT / "flags.yaml")
    content = {}
    for section_id in site["sections"]:
        path = CONTENT / f"{section_id}.yaml"
        if not path.exists():
            raise BuildError(f"section '{section_id}' listed in site.yaml has no {path.name}")
        content[section_id] = load_yaml(path)
    for item in site["nav"]:
        if item["id"] not in site["sections"]:
            raise BuildError(f"nav entry '{item['id']}' is not a section")
    return site, flags, content


def iter_media(node, path="content"):
    """Yield (path, media_dict) for every mapping that has a 'type' key."""
    if isinstance(node, dict):
        if "type" in node and isinstance(node["type"], str):
            yield path, node
        for k, v in node.items():
            yield from iter_media(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_media(v, f"{path}[{i}]")


def validate(content: dict, flags: dict) -> list[str]:
    errors = []
    for path, m in iter_media(content):
        gated_off = bool(m.get("flag")) and not flags.get(m["flag"], False)
        if m.get("flag") and m["flag"] not in flags:
            errors.append(f"{path}: unknown flag '{m['flag']}'")
        if m["type"] in MEDIA_TYPES_NEEDING_ALT and not m.get("alt"):
            errors.append(f"{path}: media of type {m['type']} needs 'alt'")
        if gated_off:
            continue  # its assets may not exist yet; the fallback is validated on its own
        for key in ("src", "webm", "poster"):
            value = m.get(key)
            if value and m["type"] != "youtube" or (m["type"] == "youtube" and key == "poster" and value):
                if value and not (ROOT / value).exists():
                    errors.append(f"{path}.{key}: missing file {value}")
    return errors


# -------------------------------------------------------------- rendering ----
def make_env(site: dict, flags: dict, content: dict, manifest: dict) -> Environment:
    env = Environment(
        loader=FileSystemLoader(SRC / "templates"),
        undefined=ChainableUndefined,
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def inline_svg(name: str) -> Markup:
        path = SRC / "svg" / name
        if not path.exists():
            raise BuildError(f"inline_svg: missing {path.relative_to(ROOT)}")
        return Markup(path.read_text(encoding="utf-8").strip())

    class Dims(dict):
        __getattr__ = dict.__getitem__

    def dims(path: str) -> Dims:
        if path in manifest:
            return Dims(manifest[path])
        try:
            from PIL import Image
            with Image.open(ROOT / path) as im:
                return Dims(width=im.width, height=im.height)
        except Exception as exc:  # noqa: BLE001
            raise BuildError(f"dims: cannot read {path}: {exc}") from exc

    refs = content.get("references", {}).get("entries", [])
    ref_index = {r["id"]: i + 1 for i, r in enumerate(refs)}
    env.globals.update(site=site, flags=flags, content=content, inline_svg=inline_svg, dims=dims, ref_index=ref_index)
    return env


def concat_css(site: dict) -> str:
    styles = SRC / "styles"
    order = [styles / "tokens.css", styles / "base.css", styles / "layout.css"]
    order += sorted((styles / "components").glob("*.css"))
    order += [p for p in ((styles / "sections" / f"{s}.css") for s in site["sections"]) if p.exists()]
    parts = [f"/* ---- {p.relative_to(styles)} ---- */\n{p.read_text(encoding='utf-8').strip()}\n" for p in order]
    return "\n".join(parts)


def copy_tree(src: Path, dst: Path, ignore_names: set[str] = frozenset()) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=lambda d, names: [n for n in names if n in ignore_names])


def size_report(root: Path) -> list[tuple[str, int]]:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rows.append((str(p.relative_to(root)), p.stat().st_size))
    return rows


# ------------------------------------------------------------------- main ----
def build(verbose: bool = True) -> Path:
    site, flags, content = load_content()
    errors = validate(content, flags)
    if errors:
        raise BuildError("content validation failed:\n  - " + "\n  - ".join(errors))

    manifest_path = ASSETS / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    env = make_env(site, flags, content, manifest)

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "styles").mkdir(parents=True)

    html = env.get_template("index.html.j2").render()
    (DIST / "index.html").write_text(html, encoding="utf-8")
    (DIST / "styles" / "site.css").write_text(concat_css(site), encoding="utf-8")
    copy_tree(SRC / "scripts", DIST / "scripts")
    copy_tree(SRC / "static", DIST)
    copy_tree(ASSETS, DIST / "assets", ignore_names={"manifest.json"})

    if verbose:
        rows = size_report(DIST)
        total = sum(s for _, s in rows)
        print(f"[build] dist/ written: {len(rows)} files, {total / 1e6:.1f} MB total")
        for name, size in rows:
            if size > 1_000_000:
                print(f"         {size / 1e6:6.1f} MB  {name}")
    return DIST


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()
    try:
        build(verbose=not args.quiet)
    except BuildError as exc:
        print(f"[build] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
