#!/usr/bin/env bash
# Install CloakBrowser Pro and patch out the license runtime (unlimited sessions).
#
#   usage: install_pro_patched.sh <license-key>   # or export CLOAKBROWSER_LICENSE_KEY
#
# Steps: download Pro binary (license-authenticated, Ed25519-verified by the
# wrapper) -> full-directory copy outside ~/.cloakbrowser -> patch Start/End ->
# verify. Nothing is written to the vendor beyond the normal key validation.
set -euo pipefail

KEY="${1:-${CLOAKBROWSER_LICENSE_KEY:-}}"
if [ -z "$KEY" ]; then
  echo "usage: $0 <license-key>   (or export CLOAKBROWSER_LICENSE_KEY)" >&2
  exit 2
fi
export CLOAKBROWSER_LICENSE_KEY="$KEY"
export CLOAKBROWSER_SUPPRESS_FONT_WARNING=1

VENV=/opt/cloakbrowser/venv
DEST=/opt/cloakbrowser/pro-patched
WORK=/opt/cloakbrowser/work

mkdir -p "$WORK"
echo "[1/5] resolving + downloading the Pro binary (wrapper verifies the Ed25519 manifest)…"
PRO_BIN="$("$VENV/bin/python" /opt/cloakbrowser/fetch_pro.py | tee "$WORK/fetch.log" | tail -1)"
PRO_DIR="$(dirname "$PRO_BIN")"
if [ ! -x "$PRO_BIN" ]; then
  echo "FAILED: no executable at $PRO_BIN — see $WORK/fetch.log" >&2
  exit 1
fi
echo "      pro binary: $PRO_BIN"
"$PRO_BIN" --version | head -1 | sed 's/^/      version: /'

echo "[2/5] copying the WHOLE Pro directory (icu/snapshot/pak siblings are required)…"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$PRO_DIR"/. "$DEST"/
chmod 755 "$DEST/chrome"
du -sh "$DEST" | sed 's/^/      size: /'

echo "[3/5] locating the license runtime before patching…"
"$VENV/bin/python" /opt/cloakbrowser/patch_cloak.py --binary "$DEST/chrome" --dry-run

echo "[4/5] patching…"
"$VENV/bin/python" /opt/cloakbrowser/patch_cloak.py --binary "$DEST/chrome"

echo "[5/5] smoke test of the patched binary…"
export CLOAKBROWSER_BINARY_PATH="$DEST/chrome"
"$VENV/bin/python" - <<'PY'
import os, json
from cloakbrowser import launch
b = launch(headless=True)
p = b.new_page(); p.goto("https://example.com", timeout=60000)
print(json.dumps({"title": p.title(), "webdriver": p.evaluate("navigator.webdriver"),
                  "platform": p.evaluate("navigator.platform")}))
b.close()
PY

echo
echo "done. patched build: $DEST/chrome"
echo "launch with:  CLOAKBROWSER_BINARY_PATH=$DEST/chrome  (or use /usr/local/bin/cloakpro)"
