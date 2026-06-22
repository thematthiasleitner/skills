#!/usr/bin/env bash
# runner.sh — smoke test for alps-post-render.
# Renders a minimal 1080x1350 slide via the documented headless-Chrome command
# and asserts the 2x export is exactly 2160x2700. Hermetic (temp dir), no deps
# beyond Chrome + sips. Exit non-zero on any failure.
set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$CHROME" ]; then
  echo "FAIL: Google Chrome not found at: $CHROME"
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/slide.html" <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0}
  .post{width:1080px;height:1350px;background:#050007;color:#fff;
        font:700 90px sans-serif;display:grid;place-items:center}
</style></head><body><div class="post">ALPS</div></body></html>
HTML

OUT="$TMP/out.png"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=1080,1350 --default-background-color=050007ff --virtual-time-budget=3500 \
  --screenshot="$OUT" "file://$TMP/slide.html" >/dev/null 2>&1 || true

if [ ! -f "$OUT" ]; then
  echo "FAIL: no PNG produced"
  exit 1
fi

W=$(sips -g pixelWidth  "$OUT" | awk '/pixelWidth/{print $2}')
H=$(sips -g pixelHeight "$OUT" | awk '/pixelHeight/{print $2}')

if [ "$W" = "2160" ] && [ "$H" = "2700" ]; then
  echo "PASS: rendered ${W}x${H} (2x of 1080x1350)"
  exit 0
fi

echo "FAIL: expected 2160x2700, got ${W}x${H}"
exit 1
