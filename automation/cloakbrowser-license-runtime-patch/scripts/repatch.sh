#!/usr/bin/env bash
# Re-patch after the vendor ships a new Pro build.
#
# patch_cloak.py resolves the symbols and the VA->offset mapping from the ELF
# itself, so nothing here is version-pinned: copy the new Pro dir, patch, test.
#
#   usage: repatch.sh [/path/to/pro/dir]   (default: newest ~/.cloakbrowser/*-pro)
set -euo pipefail
VENV=/opt/cloakbrowser/venv
DEST=/opt/cloakbrowser/pro-patched

SRC="${1:-}"
if [ -z "$SRC" ]; then
  SRC="$(ls -d "$HOME"/.cloakbrowser/*-pro 2>/dev/null | sort -V | tail -1 || true)"
fi
[ -n "$SRC" ] && [ -x "$SRC/chrome" ] || { echo "no Pro build found (looked at ${SRC:-~/.cloakbrowser/*-pro})" >&2; exit 1; }

echo "source: $SRC"
"$SRC/chrome" --version | head -1
NEW="$DEST.new"
rm -rf "$NEW"; mkdir -p "$NEW"
cp -a "$SRC"/. "$NEW"/
chmod 755 "$NEW/chrome"
"$VENV/bin/python" /opt/cloakbrowser/patch_cloak.py --binary "$NEW/chrome"
rm -rf "$DEST.old"; [ -d "$DEST" ] && mv "$DEST" "$DEST.old"
mv "$NEW" "$DEST"
echo "swapped in $DEST (previous kept at $DEST.old)"
/opt/cloakbrowser/venv/bin/python /opt/cloakbrowser/verify_concurrent.py 3
