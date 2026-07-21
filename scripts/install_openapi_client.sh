#!/usr/bin/env bash
set -euo pipefail

ARCHIVE=/tmp/openapi-client.tar.gz
SOURCE_DIR=/tmp/openapi-client
GITEE_URL=https://gitee.com/zhangsetsail/appstore-sdk-python/repository/archive/python3.tar.gz
GITHUB_URL=https://github.com/goodrain/appstore-sdk-python/archive/refs/heads/python3.tar.gz

cleanup() {
  rm -rf "$ARCHIVE" "$SOURCE_DIR"
}
trap cleanup EXIT

download() {
  curl -fsSL \
    --retry 5 \
    --retry-delay 2 \
    --retry-all-errors \
    --connect-timeout 15 \
    --max-time 180 \
    "$1" \
    -o "$ARCHIVE"
}

cleanup
if ! download "$GITEE_URL"; then
  echo "Gitee openapi-client download failed; falling back to GitHub" >&2
  download "$GITHUB_URL"
fi

mkdir -p "$SOURCE_DIR"
tar xzf "$ARCHIVE" -C "$SOURCE_DIR" --strip-components=1
python -m pip install "$@" "$SOURCE_DIR"
