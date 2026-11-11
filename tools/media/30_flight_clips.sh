#!/usr/bin/env bash
# Priority 2: six per-flight loops (720p) from the REAL video, plus the YouTube
# facade poster. In/out points come from edl/flights.yaml.
source "$(dirname "$0")/_common.sh"
PY="$ROOT/.venv/bin/python"
EDL="$ROOT/tools/media/edl/flights.yaml"

echo "[flights] facade poster"
ffmpeg -loglevel error -y -ss 12 -i "$REAL" -frames:v 1 \
  -vf "scale=1600:900:flags=lanczos" -q:v 3 "$ASSETS/img/posters/real-youtube-poster.jpg"

mapfile -t CLIPS < <("$PY" - "$EDL" <<'PYEOF'
import sys, yaml
def s(t): m, sec = str(t).split(":"); return int(m)*60 + float(sec)
for c in yaml.safe_load(open(sys.argv[1]))["clips"]:
    print(f'{c["id"]}|{s(c["in"])}|{s(c["out"]) - s(c["in"])}')
PYEOF
)
for line in "${CLIPS[@]}"; do
  IFS='|' read -r id a d <<< "$line"
  out="$ASSETS/video/flights/$id.mp4"
  ffmpeg -loglevel error -y -ss "$a" -t "$d" -i "$REAL" \
    -vf "scale=1280:720:flags=lanczos,fps=30" -crf 26 "${H264[@]}" "$out"
  ffmpeg -loglevel error -y -i "$out" -crf 36 "${VP9[@]}" "${out%.mp4}.webm"
  ffmpeg -loglevel error -y -i "$out" -frames:v 1 -q:v 4 "${out%.mp4}-poster.jpg"
  echo "[flights] $id (${d}s)"
done
report "$ASSETS"/video/flights/*.mp4
