#!/usr/bin/env bash
# Build the visual-only judging timeline (exactly 2 minutes 48 seconds).
#
# It deliberately uses only the configured architecture and a labeled fixture
# dashboard until genuine GitHub scheduled-run and webhook evidence is
# available. Do not call this a final Track 2 proof video without replacing
# the pending shots described in submission/judging-video-script.md.
set -euo pipefail

output_path="${1:-submission/marketops-judging-visual-no-voice.mp4}"
architecture="submission/assets/architecture.png"
dashboard="submission/assets/dashboard.png"

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required. See submission/video-assembly.md." >&2
  exit 1
}

for asset in "$architecture" "$dashboard"; do
  [[ -f "$asset" ]] || {
    echo "Missing demo asset: $asset" >&2
    exit 1
  }
done

mkdir -p "$(dirname "$output_path")"

ffmpeg -hide_banner -y \
  -framerate 30 -loop 1 -t 30 -i "$architecture" \
  -framerate 30 -loop 1 -t 138 -i "$dashboard" \
  -filter_complex "\
    [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#0a0d13,setsar=1[a];\
    [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#0a0d13,setsar=1[b];\
    [a][b]concat=n=2:v=1:a=0,format=yuv420p[v]" \
  -map "[v]" -r 30 -c:v libx264 -crf 20 -preset medium -movflags +faststart \
  "$output_path"

echo "Built visual-only 2:48 judging timeline: $output_path"
echo "Before publishing: add narration/captions and replace pending evidence shots with real schedule-run material."
