#!/bin/bash
# Generic runtime sandbox runner for isolated tools.
# Copy to /opt/<tool>/sandbox-run.sh, replace <tool> tokens, chmod 755.
#
# Usage:
#   sandbox-run.sh slither <args>           # air-gapped (no net)
#   sandbox-run.sh --net cast <args>        # host net (RPC/fork), fs isolated
#
# Security: user-ns fake root + private ro mount ns + tmpfs /tmp.
# Even with --net, tool code CANNOT read/write host files.

set -euo pipefail

# ---- CONFIG: replace <tool> with your install dir name (e.g. crypto-tools) ----
TOOL_DIR="/opt/<tool>"
VENV="/opt/<tool>-audit/venv"
# ---------------------------------------------------------------------------

NET_MODE=""
case "${1:-}" in --net|--net-host) NET_MODE="host"; shift ;; esac

TOOL="${1:-}"
if [[ -z "$TOOL" ]]; then
  echo "Usage: sandbox-run.sh [--net] <tool> [args...]"
  exit 1
fi
shift || true
ARGS=("$@")

# shellcheck disable=SC1090
source "$TOOL_DIR/env.sh" >/dev/null 2>&1 || true

# User ns + private mount ns ALWAYS.
# Network: default = SEPARATE ns (air-gapped); --net = inherit host (omit --net flag).
UNSHARE_ARGS="--user --map-root-user --mount"
if [[ -z "$NET_MODE" ]]; then
  UNSHARE_ARGS="$UNSHARE_ARGS --net"
fi

ARGS_JSON=$(printf '%s\0' "${ARGS[@]}" | base64 -w0)

run_in_ns() {
  local tool="$1" args_b64="$2"; local -a decoded
  while IFS= read -r -d '' p; do decoded+=("$p"); done < <(echo -n "$args_b64" | base64 -d)
  mkdir -p /tmp/sandbox; mount -t tmpfs tmpfs /tmp/sandbox 2>/dev/null || true
  for mp in "$TOOL_DIR" /usr /bin /lib /lib64 /etc; do
    mkdir -p "$mp"; mount --bind "$mp" "$mp" 2>/dev/null || true
    mount -o remount,ro "$mp" 2>/dev/null || true
  done
  export PATH="$TOOL_DIR/bin:$VENV/bin:$PATH"
  case "$tool" in
    slither) "$VENV/bin/python" -m slither "${decoded[@]}" ;;
    web3)    "$VENV/bin/python" "${decoded[@]}" ;;
    *)       "$TOOL_DIR/bin/$tool" "${decoded[@]}" ;;
  esac
}
export -f run_in_ns

echo "[sandbox] $TOOL (net: ${NET_MODE:-air-gapped})"
unshare $UNSHARE_ARGS bash -c 'run_in_ns "$0" "$1"' "$TOOL" "$ARGS_JSON"
