#!/usr/bin/env python3
"""Serve dist/ locally. With --watch, rebuild when content/, src/ or assets/ change."""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WATCHED = [ROOT / "content", ROOT / "src", ROOT / "assets"]


def snapshot() -> dict[str, float]:
    out = {}
    for base in WATCHED:
        for p in base.rglob("*"):
            if p.is_file():
                out[str(p)] = p.stat().st_mtime
    return out


def watcher(interval: float) -> None:
    last = snapshot()
    while True:
        time.sleep(interval)
        cur = snapshot()
        if cur != last:
            last = cur
            try:
                build.build(verbose=False)
                print("[watch] rebuilt")
            except build.BuildError as exc:
                print(f"[watch] build error: {exc}")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".mjs": "text/javascript", ".webp": "image/webp",
                      ".webm": "video/webm", ".svg": "image/svg+xml"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the console readable
        if "200" not in (args[1] if len(args) > 1 else ""):
            super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    try:
        build.build(verbose=False)
    except build.BuildError as exc:
        print(f"[serve] build error: {exc}", file=sys.stderr)
        return 1
    if args.watch:
        threading.Thread(target=watcher, args=(args.interval,), daemon=True).start()
    handler = functools.partial(QuietHandler, directory=str(build.DIST))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"[serve] http://localhost:{args.port}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
