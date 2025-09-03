#!/usr/bin/env bash
# Create first-frame thumbnails for README placeholders.
# Outputs 960w and 480w JPGs into demos/thumbs/ for each demos/*.gif

set -euo pipefail
mkdir -p demos/thumbs

for gif in demos/*.gif; do
  base="$(basename "$gif" .gif)"

  # 960-wide thumbnail (banner)
  ffmpeg -y -v error -i "$gif" \
    -frames:v 1 -vf "scale=960:-2:flags=lanczos" \
    "demos/thumbs/${base}_thumb_960.jpg"

  # 480-wide thumbnail (grid cards)
  ffmpeg -y -v error -i "$gif" \
    -frames:v 1 -vf "scale=480:-2:flags=lanczos" \
    "demos/thumbs/${base}_thumb_480.jpg"

  echo "✓ demos/thumbs/${base}_thumb_{960,480}.jpg"
done
