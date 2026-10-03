#!/usr/bin/env bash
# Fetch a static FFmpeg with the WHIP muxer into .tools/ffmpeg.
# Only used by the E2E suite, where FFmpeg stands in for OBS (WHIP + stream key).
# Pinned build, verified by checksum.
set -euo pipefail

TAG="autobuild-2026-10-01-13-06"
FILE="ffmpeg-n9.0.2-22-g46d8f462ee-linux64-gpl-9.0.tar.xz"
SHA256="a6170faecf757381ad0338d7a6ba26e97c2ebe2b9c1568633421e15d1ed436a9"

cd "$(dirname "$0")/.."
if [[ -x .tools/ffmpeg ]] && .tools/ffmpeg -hide_banner -muxers 2>/dev/null | grep -q whip; then
  echo "FFmpeg mit WHIP ist schon da (.tools/ffmpeg)."
  exit 0
fi
[[ "$(uname -m)" == x86_64 ]] || { echo "Nur für x86_64 hinterlegt." >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://github.com/BtbN/FFmpeg-Builds/releases/download/$TAG/$FILE" -o "$TMP/$FILE"
echo "$SHA256  $TMP/$FILE" | sha256sum -c --quiet
mkdir -p .tools
tar -xJf "$TMP/$FILE" -C "$TMP" --wildcards '*/bin/ffmpeg'
mv "$TMP"/*/bin/ffmpeg .tools/ffmpeg
echo "FFmpeg installiert: $(.tools/ffmpeg -hide_banner -version | head -1)"
