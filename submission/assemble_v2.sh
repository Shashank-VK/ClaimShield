#!/usr/bin/env bash
# Assemble the ClaimShield Desk v2 final cut.
# NLM slices (muted, upscaled 720p->1080p) + product proof moments (gentle zoom
# 1.00->1.04, headline-safe) + Fenrir voice as master track, hard cuts (gap 0).
# Output: submission/claimshield-desk-demo-final-v2.mp4 (1920x1080, 30fps).
# Usage: assemble_v2.sh [--plan]   --plan prints the per-section allocation
# table without encoding. The real build refuses to run if any voice clip is
# missing (never ships a partial video silently).
# Allocation: product plays full (capped so >=5s remains for NLM when the
# section has any), NLM shares the remainder equally. Product trims keep the
# END of the clip (the payoff: VETO / BLOCKED / toast); NLM trims from the
# start (establishing frame). If video runs short of voice, the final frame
# is frozen to fill (tpad) — the Wrap's "hold on the final frame".
set -euo pipefail

SUB="$(cd "$(dirname "$0")" && pwd)"
CUT="$SUB/cut-v2"
VO="$SUB/vo"
WORK="$SUB/build-v2"
OUT="$SUB/claimshield-desk-demo-final-v2.mp4"

# section | voice file | segments in order (file:kind, kind=nlm|prod)
SECTIONS=(
  "s1-hook|v2-s1-hook.mp3|hook-clip.mp4:nlm"   # hook visual = HIS clip (denied claim form, hand writes APPEAL), zoomed 1.25x to hide the Gemini watermark, slowed 0.5x + held tail — replaced the generated still 7 Nov 17:27 IST on his call; hook-opener.mp4 retired
  "s2-problem|v2-s2-problem.mp3|nlm-problem.mp4:nlm"
  "s3-turn|v2-s3-turn.mp3|nlm-turn.mp4:nlm,prod-beat1.mp4:prod"
  "s4-scrub|v2-s4-scrub.mp3|nlm-scrub.mp4:nlm,prod-beat2.mp4:prod"
  "s5-critic|v2-s5-critic.mp3|nlm-critic-a.mp4:nlm,nlm-critic-b.mp4:nlm,prod-beat3.mp4:prod"
  "s6-gate|v2-s6-gate.mp3|nlm-gate.mp4:nlm,prod-beat4.mp4:prod"
  "s7-wrap|v2-s7-wrap.mp3|prod-wrap.mp4:prod,nlm-close.mp4:nlm"
)

dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
fadd() { python3 -c "print($1 + $2)"; }
fmin() { python3 -c "print(min($1, $2))"; }
fmax() { python3 -c "print(max($1, $2))"; }

# allocate VOICE_DUR seg... -> lines "file kind alloc" in original order
allocate() {
  local voice_dur="$1"; shift
  local -a segs=("$@")
  local n_prod=0 n_nlm=0 prod_total=0
  local s f k
  for s in "${segs[@]}"; do
    f="${s%%:*}"; k="${s##*:}"
    if [ "$k" = prod ]; then
      n_prod=$((n_prod+1)); prod_total=$(fadd "$prod_total" "$(dur "$CUT/$f")")
    else n_nlm=$((n_nlm+1)); fi
  done
  local prod_cap="$prod_total"
  if [ "$n_nlm" -gt 0 ]; then
    prod_cap=$(fmin "$prod_total" "$(fmax 0 "$(python3 -c "print($voice_dur - 5.0)")")")
  fi
  local prod_left="$prod_cap"
  local -a allocs=()
  for s in "${segs[@]}"; do
    f="${s%%:*}"; k="${s##*:}"
    if [ "$k" = prod ]; then
      d=$(dur "$CUT/$f")
      a=$(fmin "$d" "$prod_left")
      prod_left=$(fmax 0 "$(python3 -c "print($prod_left - $a)")")
      allocs+=("$f:prod:$a")
    fi
  done
  local nlm_total=$(fmax 0 "$(python3 -c "print($voice_dur - $prod_cap)")")
  local nlm_each=0
  [ "$n_nlm" -gt 0 ] && nlm_each=$(python3 -c "print($nlm_total / $n_nlm)")
  for s in "${segs[@]}"; do
    f="${s%%:*}"; k="${s##*:}"
    [ "$k" = nlm ] && allocs+=("$f:nlm:$nlm_each")
  done
  for s in "${segs[@]}"; do
    f="${s%%:*}"
    for a in "${allocs[@]}"; do
      [ "${a%%:*}" = "$f" ] && echo "$a"
    done
  done
}

PLAN_ONLY=0
[ "${1:-}" = "--plan" ] && PLAN_ONLY=1

missing=()
for row in "${SECTIONS[@]}"; do
  IFS='|' read -r slug voice segstr <<< "$row"
  IFS=',' read -r -a segarr <<< "$segstr"
  if [ ! -f "$VO/$voice" ]; then
    missing+=("$voice")
    echo "$slug | voice $voice MISSING"
    continue
  fi
  V=$(dur "$VO/$voice")
  echo "$slug | voice ${V}s"
  while IFS=: read -r f k a; do
    echo "    $f ($k) -> ${a}s"
  done < <(allocate "$V" "${segarr[@]}")
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "MISSING VOICE: ${missing[*]} — build refused (no partial video)."
  exit 1
fi
[ "$PLAN_ONLY" -eq 1 ] && exit 0

mkdir -p "$WORK"
rm -f "$WORK"/section-*.mp4 "$WORK/sections.txt"
i=0
for row in "${SECTIONS[@]}"; do
  IFS='|' read -r slug voice segstr <<< "$row"
  IFS=',' read -r -a segarr <<< "$segstr"
  V=$(dur "$VO/$voice")
  mapfile -t allocs < <(allocate "$V" "${segarr[@]}")
  inputs=(); fc=""; vlabels=""
  j=0
  for a in "${allocs[@]}"; do
    IFS=: read -r f k al <<< "$a"
    inputs+=(-i "$CUT/$f")
    if [ "$k" = nlm ]; then
      fc+="[${j}:v]trim=0:${al},setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos,fps=30[v${j}];"
    else
      fd=$(dur "$CUT/$f")
      start=$(fmax 0 "$(python3 -c "print($fd - $al)")")
      fc+="[${j}:v]trim=${start}:${fd},setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos,fps=30,zoompan=z='min(1+0.04*in/(30*${al}),1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30[v${j}];"
    fi
    vlabels+="[v${j}]"
    j=$((j+1))
  done
  echo "== $slug: voice ${V}s =="
  ffmpeg -v error -y "${inputs[@]}" -filter_complex "${fc}${vlabels}concat=n=${#allocs[@]}:v=1:a=0,tpad=stop_mode=clone:stop_duration=10,trim=0:${V},setpts=PTS-STARTPTS[v]" \
    -map "[v]" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 30 -an "$WORK/section-${i}.mp4"
  echo "file '$WORK/section-${i}.mp4'" >> "$WORK/sections.txt"
  i=$((i+1))
done

[ "$(ls "$VO"/v2-s*.mp3 | wc -l)" -eq 7 ] || { echo "expected 7 voice clips"; exit 1; }
AUDIO_CONCAT="concat:$(ls "$VO"/v2-s*.mp3 | tr '\n' '|' | sed 's/|$//')"

ffmpeg -v error -y -f concat -safe 0 -i "$WORK/sections.txt" -i "$AUDIO_CONCAT" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ac 2 -shortest "$OUT"
echo "DONE $OUT"
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate -show_entries format=duration -of default=nw=1 "$OUT"
