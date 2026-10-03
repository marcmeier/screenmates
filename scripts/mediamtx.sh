#!/usr/bin/env bash
# Fetch the MediaMTX media server used by the Kino into .tools/mediamtx.
# Pinned version; the amd64 build is additionally pinned by checksum.
set -euo pipefail

VERSION="v1.21.1"
SHA256_AMD64="653abc672a3e693f8d3b2717752492fdcfb8072291ec108d03d3dd857411b0ee"

cd "$(dirname "$0")/.."
DEST=".tools"
if [[ -x "$DEST/mediamtx" ]] && "$DEST/mediamtx" --version 2>/dev/null | grep -q "$VERSION"; then
  echo "MediaMTX $VERSION ist schon da ($DEST/mediamtx)."
  exit 0
fi

case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64 | arm64) ARCH=arm64 ;;
  *) echo "Nicht unterstützte Architektur: $(uname -m)" >&2; exit 1 ;;
esac
FILE="mediamtx_${VERSION}_linux_${ARCH}.tar.gz"
BASE="https://github.com/bluenviron/mediamtx/releases/download/${VERSION}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "$BASE/$FILE" -o "$TMP/$FILE"
if [[ "$ARCH" == amd64 ]]; then
  echo "$SHA256_AMD64  $TMP/$FILE" | sha256sum -c --quiet
else
  curl -fsSL "$BASE/checksums.sha256" | grep " \*$FILE\$" | sed "s# \*# $TMP/#" | sha256sum -c --quiet
fi
mkdir -p "$DEST"
tar -xzf "$TMP/$FILE" -C "$DEST" mediamtx
echo "MediaMTX $VERSION installiert: $DEST/mediamtx"
