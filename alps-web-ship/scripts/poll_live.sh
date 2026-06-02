#!/usr/bin/env bash
# Poll a URL until a marker string appears in the response body (Cloudflare deploy check).
# Usage: poll_live.sh <url> <marker> [timeout_seconds] [interval_seconds]
# Exit 0 when the marker is found; exit 1 on timeout.
set -u
url="${1:?usage: poll_live.sh <url> <marker> [timeout] [interval]}"
marker="${2:?missing marker}"
timeout="${3:-360}"
interval="${4:-20}"
deadline=$(( $(date +%s) + timeout ))
while :; do
  body="$(curl -fsS "$url" 2>/dev/null || true)"
  if printf '%s' "$body" | grep -qF -- "$marker"; then
    echo "LIVE ✓  marker found: $marker"
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "TIMEOUT after ${timeout}s — marker not found: $marker"
    exit 1
  fi
  echo "  $(date +%H:%M:%S) waiting for deploy…"
  sleep "$interval"
done
