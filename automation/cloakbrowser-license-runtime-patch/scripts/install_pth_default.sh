#!/usr/bin/env bash
# Make the patched build the default for anything running in the CloakBrowser
# venv, via a .pth that executes at interpreter start.
#
#   install_pth_default.sh          # enable
#   install_pth_default.sh --remove # disable
set -euo pipefail
SP="$(/opt/cloakbrowser/venv/bin/python -c 'import site; print(site.getsitepackages()[0])')"
PTH="$SP/zzz_cloakpro_default.pth"
if [ "${1:-}" = "--remove" ]; then
  rm -f "$PTH" && echo "removed $PTH"
  exit 0
fi
if [ ! -x /opt/cloakbrowser/pro-patched/chrome ]; then
  echo "refusing: /opt/cloakbrowser/pro-patched/chrome is not executable yet" >&2
  exit 1
fi
printf '%s\n' 'import os; os.environ.setdefault("CLOAKBROWSER_BINARY_PATH", "/opt/cloakbrowser/pro-patched/chrome"); os.environ.setdefault("CLOAKBROWSER_AUTO_UPDATE", "false")' > "$PTH"
echo "wrote $PTH"
/opt/cloakbrowser/venv/bin/python -c 'import os; print("venv default binary:", os.environ.get("CLOAKBROWSER_BINARY_PATH"))'
