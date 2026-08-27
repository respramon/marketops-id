#!/usr/bin/env bash
# Build the visual-only public teaser timeline (exactly 57 seconds).
#
# This intentionally contains no voice-over. Add the narration in
# submission/teaser-script.md and import submission/teaser-captions.srt in an
# editor before publishing. The selected dashboard image is a SANITIZED
# HISTORICAL REPLAY and must never be presented as live scheduled-run proof.
set -euo pipefail

output_path="${1:-submission/marketops-teaser-visual-no-voice.mp4}"
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
  -framerate 30 -loop 1 -t 15 -i "$architecture" \
  -framerate 30 -loop 1 -t 42 -i "$dashboard" \
  -filter_complex "\
    [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#0a0d13,setsar=1[a];\
    [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#0a0d13,setsar=1[b];\
    [a][b]concat=n=2:v=1:a=0,format=yuv420p[v]" \
  -map "[v]" -r 30 -c:v libx264 -crf 20 -preset medium -movflags +faststart \
  "$output_path"

echo "Built visual-only 57-second teaser: $output_path"
echo "Before publishing: add narration/captions and retain the fixture replay disclosure."
