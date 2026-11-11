#!/usr/bin/env bash
# Replanning / prefix-stitch animation for method step 5: 720p30 silent loop (mp4 + webm) and a poster
# taken from the final frame, so the still image already shows the finished hand-off.
source "$(dirname "$0")/_common.sh"

SRC="$MEDIA/Videos/Prefix_Stitch_Replan.mp4"
OUT_MP4="$ASSETS/video/handoff.mp4"; OUT_WEBM="$ASSETS/video/handoff.webm"; POSTER="$ASSETS/video/handoff-poster.jpg"

echo "[handoff] encode"
ffmpeg -loglevel error -y -i "$SRC" -vf "scale=1280:-2:flags=lanczos,fps=30" -crf 23 "${H264[@]}" "$OUT_MP4"
ffmpeg -loglevel error -y -i "$OUT_MP4" -crf 33 "${VP9[@]}" "$OUT_WEBM"
ffmpeg -loglevel error -y -sseof -0.2 -i "$OUT_MP4" -frames:v 1 -q:v 5 "$POSTER"

report "$OUT_MP4" "$OUT_WEBM" "$POSTER"
