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
  # Ubuntu 24.04's ffmpeg dependency set is large and hosted-runner mirror
  # throughput varies. A short install timeout repeatedly discards progress.
  # Use one bounded install with apt's own retry support so partial downloads
  # can be reused; keep the hard failure if either executable is absent.
  timeout 120s sudo apt-get update -qq -o Acquire::Retries=2
  if ! timeout 600s sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -o Acquire::Retries=2 ffmpeg; then
    echo "::error::Cannot install free system ffmpeg/ffprobe; refusing an unverified render." >&2
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
