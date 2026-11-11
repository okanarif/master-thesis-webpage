#!/usr/bin/env bash
# Hero loop from the EDL in edl/hero.yaml: trims each segment to an intermediate,
# cross-fades them, encodes mp4 + webm, extracts a poster.
# Requires: ffmpeg, python3 with PyYAML (the repo's .venv), DejaVu fonts for the end card.
source "$(dirname "$0")/_common.sh"

PY="$ROOT/.venv/bin/python"
EDL="$ROOT/tools/media/edl/hero.yaml"
TMP="$PROXIES/hero_tmp"; mkdir -p "$TMP"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Flatten the YAML into shell-friendly lines: "idx|src|in|out|duration"
mapfile -t SEGS < <("$PY" - "$EDL" <<'PYEOF'
import sys, yaml
edl = yaml.safe_load(open(sys.argv[1]))
o = edl["output"]
print(f'OUT|{o["width"]}|{o["height"]}|{o["fps"]}|{o["crf_mp4"]}|{o["crf_webm"]}|{o["xfade"]}|{o["poster_at"]}')
print(f'CARD|{edl["endcard"]["title"]}|{edl["endcard"]["line"]}')
def s(t):
    if isinstance(t,(int,float)): return float(t)
    m, sec = t.split(":"); return int(m)*60 + float(sec)
for i, seg in enumerate(edl["segments"]):
    if seg["src"] == "ENDCARD":
        print(f'{i}|ENDCARD|0|0|{seg["duration"]}')
    else:
        a, b = s(seg["in"]), s(seg["out"])
        print(f'{i}|{seg["src"]}|{a}|{b}|{b-a}')
PYEOF
)

IFS='|' read -r _ W H FPS CRF_MP4 CRF_WEBM XF POSTER_AT <<< "${SEGS[0]}"
IFS='|' read -r _ CARD_TITLE CARD_LINE <<< "${SEGS[1]}"
SEGS=("${SEGS[@]:2}")

src_path() {
  case "$1" in
    REAL) echo "$REAL" ;;
    SIM_Q1|SIM_Q2|SIM_Q3|SIM_Q4) echo "$PROXIES/sim_map${1: -1}_1080.mp4" ;;
    *) echo "unknown src $1" >&2; exit 1 ;;
  esac
}

# 1) intermediates, all identical in size / fps / pixel format
FILES=(); DURS=()
for line in "${SEGS[@]}"; do
  IFS='|' read -r i src a b d <<< "$line"
  f="$TMP/seg_$i.mp4"
  if [[ "$src" == "ENDCARD" ]]; then
    # Title card: dark background, wrapped title, attribution line.
    "$PY" - "$TMP/endcard.png" "$W" "$H" "$CARD_TITLE" "$CARD_LINE" "$FONT" "$FONT_B" <<'PYEOF'
import sys, textwrap
from PIL import Image, ImageDraw, ImageFont
out, W, H, title, line, font, font_b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), *sys.argv[4:8]
im = Image.new("RGB", (W, H), (11, 15, 20)); d = ImageDraw.Draw(im)
ft = ImageFont.truetype(font_b, int(H*0.052)); fl = ImageFont.truetype(font, int(H*0.03))
lines = textwrap.wrap(title, 38)
y = H*0.30
for t in lines:
    w = d.textlength(t, font=ft); d.text(((W-w)/2, y), t, font=ft, fill=(230, 237, 243)); y += ft.size*1.25
y += H*0.06
w = d.textlength(line, font=fl); d.text(((W-w)/2, y), line, font=fl, fill=(154, 167, 180))
im.save(out)
PYEOF
    ffmpeg -loglevel error -y -loop 1 -framerate "$FPS" -t "$d" -i "$TMP/endcard.png" \
      -vf "format=yuv420p" -c:v libx264 -preset fast -crf 18 "$f"
  else
    in_path="$(src_path "$src")"
    ffmpeg -loglevel error -y -ss "$a" -t "$d" -i "$in_path" \
      -vf "scale=${W}:${H}:flags=lanczos:force_original_aspect_ratio=increase,crop=${W}:${H},fps=${FPS},format=yuv420p" \
      -c:v libx264 -preset fast -crf 18 -an "$f"
  fi
  FILES+=("$f"); DURS+=("$d")
  echo "[hero] segment $i ($src, ${d}s) done"
done

# 2) chain xfades: offset_k = sum(dur_0..k) - (k+1)*xf
INPUTS=(); for f in "${FILES[@]}"; do INPUTS+=(-i "$f"); done
FILTER=""; prev="[0:v]"; acc=0
for ((k=1; k<${#FILES[@]}; k++)); do
  acc=$(awk -v a="$acc" -v d="${DURS[$((k-1))]}" -v x="$XF" 'BEGIN{printf "%.3f", a + d - x}')
  out="[v$k]"; [[ $k -eq $((${#FILES[@]}-1)) ]] && out="[vout]"
  FILTER+="${prev}[$k:v]xfade=transition=fade:duration=${XF}:offset=${acc}${out};"
  prev="$out"
done
FILTER="${FILTER%;}"

OUT_MP4="$ASSETS/video/hero.mp4"; OUT_WEBM="$ASSETS/video/hero.webm"; POSTER="$ASSETS/video/hero-poster.jpg"
echo "[hero] cross-fading ${#FILES[@]} segments"
ffmpeg -loglevel error -y "${INPUTS[@]}" -filter_complex "$FILTER" -map "[vout]" \
  -crf "$CRF_MP4" "${H264[@]}" "$OUT_MP4"
ffmpeg -loglevel error -y -i "$OUT_MP4" -crf "$CRF_WEBM" "${VP9[@]}" "$OUT_WEBM"
ffmpeg -loglevel error -y -ss "$POSTER_AT" -i "$OUT_MP4" -frames:v 1 -q:v 3 "$POSTER"

report "$OUT_MP4" "$OUT_WEBM" "$POSTER"
