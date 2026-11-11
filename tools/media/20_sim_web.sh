#!/usr/bin/env bash
# SIM video for in-page playback: the 2x2 grid as-is, 1080p, mp4 + webm + poster.
# Also writes a 1080p proxy of each quadrant (Map 1..4) for the hero cut and G1.
source "$(dirname "$0")/_common.sh"

OUT_MP4="$ASSETS/video/sim.mp4"
OUT_WEBM="$ASSETS/video/sim.webm"
POSTER="$ASSETS/video/sim-poster.jpg"

echo "[sim] grid -> 1080p mp4"
ffmpeg -loglevel error -y -i "$SIM" \
  -vf "scale=1920:1080:flags=lanczos,fps=30" -crf 24 "${H264[@]}" "$OUT_MP4"

echo "[sim] mp4 -> webm"
ffmpeg -loglevel error -y -i "$OUT_MP4" -crf 34 "${VP9[@]}" "$OUT_WEBM"

echo "[sim] poster"
ffmpeg -loglevel error -y -ss 0.5 -i "$OUT_MP4" -frames:v 1 -q:v 3 "$POSTER"

echo "[sim] quadrant proxies (1080p each)"
# quadrant order in the source: Map 1 top-left, Map 2 top-right, Map 3 bottom-left, Map 4 bottom-right
declare -A Q=( [1]="0:0" [2]="3840:0" [3]="0:2160" [4]="3840:2160" )
for m in 1 2 3 4; do
  IFS=: read -r x y <<< "${Q[$m]}"
  ffmpeg -loglevel error -y -i "$SIM" \
    -vf "crop=3840:2160:${x}:${y},scale=1920:1080:flags=lanczos,fps=30" \
    -crf 18 -preset fast -c:v libx264 -pix_fmt yuv420p -an "$PROXIES/sim_map${m}_1080.mp4"
done

report "$OUT_MP4" "$OUT_WEBM" "$POSTER" "$PROXIES"/sim_map*_1080.mp4
