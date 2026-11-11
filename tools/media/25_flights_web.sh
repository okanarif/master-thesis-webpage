#!/usr/bin/env bash
# Full flight video for in-page playback: 1080p30 H.264 (single file, no WebM twin to keep the
# repo small) plus a poster. Target: under 50 MB (GitHub's large-file warning threshold).
source "$(dirname "$0")/_common.sh"

CRF="${CRF:-25}"
OUT="$ASSETS/video/flights.mp4"
POSTER="$ASSETS/video/flights-poster.jpg"

echo "[flights-web] REAL -> 1080p30 mp4 (crf $CRF)"
ffmpeg -loglevel error -y -i "$REAL" \
  -vf "scale=1920:1080:flags=lanczos,fps=30" -crf "$CRF" "${H264[@]}" "$OUT"

echo "[flights-web] poster"
ffmpeg -loglevel error -y -ss 12 -i "$OUT" -frames:v 1 -vf "scale=1600:-2" -q:v 7 "$POSTER"

report "$OUT" "$POSTER"
