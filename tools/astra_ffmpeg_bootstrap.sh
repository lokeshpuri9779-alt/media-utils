#!/usr/bin/env bash
# Free, bounded installation of both encoder and probe on GitHub Ubuntu.
# The long-form lane fails closed instead of treating pip success as codec QA.
set -euo pipefail

have_video_tools() {
  command -v ffmpeg >/dev/null 2>&1 &&
    command -v ffprobe >/dev/null 2>&1
}

if ! have_video_tools; then
  echo "ASTRA_CODEC_BOOTSTRAP=system_ffmpeg_missing"
  installed=0
  for attempt in 1 2; do
    if timeout 120s sudo apt-get update -qq -o Acquire::Retries=2 &&
       timeout 180s sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg; then
      installed=1
      break
    fi
    echo "ASTRA_CODEC_BOOTSTRAP_RETRY=${attempt}"
  done
  if [[ "$installed" != "1" ]]; then
    echo "::error::Cannot install free system ffmpeg/ffprobe; refusing an unverified long-form render."
    exit 1
  fi
fi

have_video_tools || {
  echo "::error::Both ffmpeg and ffprobe are required for validated MP4 rendering."
  exit 1
}
echo "ASTRA_CODEC_BOOTSTRAP=ready"
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
