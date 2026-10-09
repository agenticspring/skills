#!/usr/bin/env bash
# captcha_balance_report.sh — live balance for every captcha key in ~/.hermes/.env
#
# Output shape:  <api_key> | $<balance> | <provider>
# Funded keys first (descending), drained/zero keys in a separated tail, deduped by key value.
#
# Usage:  bash captcha_balance_report.sh [path-to-env]
# Notes:  - 2captcha and rucaptcha are ONE account pool; query 2captcha only.
#         - A key stored under two env-var names is reported once.
#         - An empty body means blocked/timeout, and is printed as such, never as $0.00.

set -u
ENV="${1:-$HOME/.hermes/.env}"
[ -r "$ENV" ] || { echo "cannot read $ENV" >&2; exit 1; }

get() { grep -m1 "^$1=" "$ENV" 2>/dev/null | cut -d= -f2- ; }
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

echo "# api_key | balance | provider   (live $(date -u '+%Y-%m-%d %H:%M:%S') UTC)"
echo

# ---- collect candidate keys, dedupe by VALUE -------------------------------
declare -A SEEN
VARS=$(grep -oE '^[A-Z0-9_]*(CAPTCHA|CAPSOLVER|CAPMONSTER|UCAPTCHA|SOLVEX|NOPECHA)[A-Z0-9_]*=' "$ENV" \
        | tr -d '=' | sort -u)
[ -n "$VARS" ] || { echo "# no captcha keys found in $ENV"; exit 0; }

# ---- 2captcha family (plain float body) ------------------------------------
for v in $VARS; do
  case "$v" in *CAPTCHA*) ;; *) continue ;; esac
  k=$(get "$v"); [ -n "$k" ] || continue
  [ -n "${SEEN[$k]:-}" ] && continue
  SEEN[$k]=1
  b=$(curl -s --max-time 20 "https://2captcha.com/res.php?key=$k&action=getbalance")
  case "$b" in
    ''|*ERROR*|*error*) ;;                                  # unknown here, other providers may match
    *) printf '%s|%s|2captcha\n' "$b" "$k" >> "$TMP" ;;
  esac
  sleep 0.35
done

# ---- capsolver -------------------------------------------------------------
for v in $VARS; do
  case "$v" in CAPSOLVER*) ;; *) continue ;; esac
  k=$(get "$v"); [ -n "$k" ] || continue
  [ -n "${SEEN[$k]:-}" ] && continue
  SEEN[$k]=1
  r=$(curl -s --max-time 20 -X POST "https://api.capsolver.com/getBalance" \
        -H "Content-Type: application/json" -d "{\"clientKey\":\"$k\"}")
  b=$(printf '%s' "$r" | sed -nE 's/.*"balance":([0-9.eE+-]+).*/\1/p')
  if [ -n "$b" ]; then printf '%s|%s|capsolver\n' "$b" "$k" >> "$TMP"
  elif [ -z "$r" ]; then printf 'X|%s|capsolver (blocked/timeout)\n' "$k" >> "$TMP"
  fi
  sleep 0.35
done

# ---- anti-captcha ----------------------------------------------------------
for v in $VARS; do
  case "$v" in *ANTICAPTCHA*) ;; *) continue ;; esac
  k=$(get "$v"); [ -n "$k" ] || continue
  [ -n "${SEEN[$k]:-}" ] && continue
  SEEN[$k]=1
  r=$(curl -s --max-time 20 -X POST "https://api.anti-captcha.com/getBalance" \
        -H "Content-Type: application/json" -d "{\"clientKey\":\"$k\"}")
  b=$(printf '%s' "$r" | sed -nE 's/.*"balance":([0-9.eE+-]+).*/\1/p')
  if [ -n "$b" ]; then printf '%s|%s|anti-captcha\n' "$b" "$k" >> "$TMP"
  elif [ -z "$r" ]; then printf 'X|%s|anti-captcha (blocked/timeout)\n' "$k" >> "$TMP"
  fi
  sleep 0.35
done

# ---- capmonster ------------------------------------------------------------
for v in $VARS; do
  case "$v" in *CAPMONSTER*) ;; *) continue ;; esac
  k=$(get "$v"); [ -n "$k" ] || continue
  [ -n "${SEEN[$k]:-}" ] && continue
  SEEN[$k]=1
  r=$(curl -s --max-time 25 -X POST "https://api.capmonster.cloud/getBalance" \
        -H "Content-Type: application/json" -d "{\"clientKey\":\"$k\"}")
  b=$(printf '%s' "$r" | sed -nE 's/.*"balance":([0-9.eE+-]+).*/\1/p')
  if [ -n "$b" ]; then printf '%s|%s|capmonster\n' "$b" "$k" >> "$TMP"
  elif [ -z "$r" ]; then printf 'X|%s|capmonster (blocked/timeout)\n' "$k" >> "$TMP"
  fi
done

# ---- render: funded (desc) then drained/zero -------------------------------
sort -t'|' -k1,1gr "$TMP" | awk -F'|' '$1+0>0'   | while IFS='|' read -r b k p; do
  printf '%s | $%-10s | %s\n' "$k" "$b" "$p"; done

echo
echo "# habis / kosong / tidak diketahui"
sort -t'|' -k1,1gr "$TMP" | awk -F'|' '$1=="X" || $1+0<=0' | while IFS='|' read -r b k p; do
  if [ "$b" = "X" ]; then printf '%s | %-10s | %s\n' "$k" "(no body)" "$p"
  else printf '%s | $%-9s | %s\n' "$k" "$b" "$p"; fi; done

echo
awk -F'|' '$1+0>0{s+=$1; n++} END{printf "# total: $%.5f across %d keys (deduped)\n", s, n}' "$TMP"
