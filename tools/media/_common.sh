#!/usr/bin/env bash
# Shared settings for the media pipeline. Sourced by the numbered scripts.
# Raw sources live in Media/ (gitignored); outputs go to assets/ (committed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MEDIA="$ROOT/Media"
ASSETS="$ROOT/assets"
PROXIES="$MEDIA/Proxies"

REAL="$MEDIA/Videos/Hardware_Video.mp4"        # 3840x2160 60fps, 147.7 s
SIM="$MEDIA/Videos/Simulation_Results.mp4"     # 7680x4320 60fps, 29.5 s (2x2 grid)

mkdir -p "$ASSETS/video" "$ASSETS/video/flights" "$ASSETS/img/figures" \
         "$ASSETS/img/photos" "$ASSETS/img/maps" "$ASSETS/img/posters" \
         "$ASSETS/img/og" "$PROXIES"

# Encoders. H.264 for broad support, VP9 as the smaller alternative source.
H264=(-c:v libx264 -preset slow -pix_fmt yuv420p -movflags +faststart -an)
VP9=(-c:v libvpx-vp9 -b:v 0 -row-mt 1 -pix_fmt yuv420p -an)

need() { command -v "$1" >/dev/null || { echo "missing: $1" >&2; exit 1; }; }
need ffmpeg
need ffprobe

size_mb() { du -m "$1" | cut -f1; }
report() { for f in "$@"; do printf '  %-48s %4s MB\n' "${f#$ROOT/}" "$(size_mb "$f")"; done; }
