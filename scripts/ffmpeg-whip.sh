#!/usr/bin/env bash
# Fetch a static FFmpeg with the WHIP muxer into .tools/ffmpeg.
# Only used by the E2E suite, where FFmpeg stands in for OBS (WHIP + stream key).
# Latest 9.0 build, verified against the checksum GitHub publishes for the asset. BtbN deletes old
# autobuilds after a few weeks, so a pinned tag breaks CI sooner or later.
set -euo pipefail

REPO="BtbN/FFmpeg-Builds"
FILE="ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz"

cd "$(dirname "$0")/.."
if [[ -x .tools/ffmpeg ]] && .tools/ffmpeg -hide_banner -muxers 2>/dev/null | grep -q whip; then
  echo "FFmpeg mit WHIP ist schon da (.tools/ffmpeg)."
  exit 0
fi
[[ "$(uname -m)" == x86_64 ]] || { echo "Nur für x86_64 hinterlegt." >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
AUTH=()
[[ -n "${GITHUB_TOKEN:-}" ]] && AUTH=(-H "Authorization: Bearer $GITHUB_TOKEN")
SHA256="$(curl -fsSL "${AUTH[@]}" "https://api.github.com/repos/$REPO/releases/tags/latest" \
  | python3 -c 'import json,sys; print(next(a["digest"] for a in json.load(sys.stdin)["assets"] if a["name"]==sys.argv[1]).removeprefix("sha256:"))' "$FILE")"
curl -fsSL "https://github.com/$REPO/releases/download/latest/$FILE" -o "$TMP/$FILE"
echo "$SHA256  $TMP/$FILE" | sha256sum -c --quiet
mkdir -p .tools
tar -xJf "$TMP/$FILE" -C "$TMP" --wildcards '*/bin/ffmpeg'
mv "$TMP"/*/bin/ffmpeg .tools/ffmpeg
echo "FFmpeg installiert: $(.tools/ffmpeg -hide_banner -version | head -1)"
