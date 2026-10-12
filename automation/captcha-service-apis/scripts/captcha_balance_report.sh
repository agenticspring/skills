#!/usr/bin/env bash
# captcha_balance_report.sh — live balance for every captcha key in ~/.hermes/.env
#
# Output shape:  <api_key> | $<balance> | <provider>
# Funded keys first (descending), drained/error keys in a separated tail, deduped by key value.
#
# Usage:  bash captcha_balance_report.sh [path-to-env]
#
# Notes:
#   - 2captcha and rucaptcha are ONE account pool; query 2captcha only.
#   - A key stored under two env-var names is reported once (first name wins).
#   - Routing is decided by the ENV VAR NAME first. A plain `*CAPTCHA*` glob also matches
#     ANTICAPTCHA_/UCAPTCHA_/CAPTCHAAI_/SOLVECAPTCHA_/NEXTCAPTCHA_ — matching those in the
#     2captcha branch marks the key as already-seen and the key's real provider then skips it,
#     so the key disappears from the report entirely (silent omission, verified 2026-10-12:
#     ANTICAPTCHA_API_KEY was live at -0.00182 and never printed). Keep the ordered
#     provider_of() classification below.
#   - Never print a key as $0.00 when the provider returned nothing / an error. An empty body is
#     a block/timeout ("X") and an error body is "X2"; both are visible, never silently dropped.
set -u
ENV="${1:-$HOME/.hermes/.env}"
[ -r "$ENV" ] || { echo "cannot read $ENV" >&2; exit 1; }

get() { grep -m1 "^$1=" "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"'\r'; }
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

# provider_of <env-var-name> — ordered: specific names BEFORE the generic *CAPTCHA* fallback.
provider_of() {
  case "$1" in
    *ANTICAPTCHA*)  echo anti-captcha ;;
    CAPSOLVER*)     echo capsolver ;;
    *CAPMONSTER*)   echo capmonster ;;
    *NEXTCAPTCHA*)  echo NextCaptcha ;;
    *SOLVECAPTCHA*) echo SolveCaptcha ;;
    *CAPTCHAAI*)    echo CaptchaAI ;;
    *UCAPTCHA*)     echo uCaptcha ;;
    *SOLVEX*)       echo Solvex ;;
    *CAPTCHA*)      echo 2captcha ;;
    *)              echo "" ;;
  esac
}

# post_balance <provider> <url> <key>     — JSON body {"clientKey":...}
post_balance() {
  local r b
  r=$(curl -s --max-time 20 -X POST "$2" -H "Content-Type: application/json" -d "{\"clientKey\":\"$3\"}")
  b=$(printf '%s' "$r" | sed -nE 's/.*"balance":([0-9.eE+-]+).*/\1/p')
  if   [ -n "$b" ];    then printf '%s|%s|%s\n'  "$b" "$3" "$1" >> "$TMP"
  elif [ -z "$r" ];    then printf 'X|%s|%s (blocked/timeout)\n' "$3" "$1" >> "$TMP"
  else printf 'X2|%s|%s (error: %s)\n' "$3" "$1" "$(printf '%s' "$r" | tr -d '\n' | head -c 70)" >> "$TMP"
  fi
}

# get_balance <provider> <url> <key>      — JSON body {"status":1,"balance":...}
get_balance() {
  local r b
  r=$(curl -s --max-time 20 "$2")
  b=$(printf '%s' "$r" | sed -nE 's/.*"balance":([0-9.eE+-]+).*/\1/p')
  if   [ -n "$b" ];    then printf '%s|%s|%s\n'  "$b" "$3" "$1" >> "$TMP"
  elif [ -z "$r" ];    then printf 'X|%s|%s (blocked/timeout)\n' "$3" "$1" >> "$TMP"
  else printf 'X2|%s|%s (error: %s)\n' "$3" "$1" "$(printf '%s' "$r" | tr -d '\n' | head -c 70)" >> "$TMP"
  fi
}

echo "# api_key | balance | provider   (live $(date -u '+%Y-%m-%d %H:%M:%S') UTC)"
echo

declare -A SEEN
VARS=$(grep -oE '^[A-Z0-9_]*(CAPTCHA|CAPSOLVER|CAPMONSTER|UCAPTCHA|SOLVEX|NOPECHA)[A-Z0-9_]*=' "$ENV" \
        | tr -d '=' | sort -u)
[ -n "$VARS" ] || { echo "# no captcha keys found in $ENV"; exit 0; }

for v in $VARS; do
  k=$(get "$v"); [ -n "$k" ] || continue
  [ -n "${SEEN[$k]:-}" ] && continue          # dedupe by key VALUE
  SEEN[$k]=1
  case "$(provider_of "$v")" in
    2captcha)      # same backend pool as rucaptcha — query once
                   b=$(curl -s --max-time 20 "https://2captcha.com/res.php?key=$k&action=getbalance")
                   case "$b" in
                     ''|*ERROR*|*error*) printf 'X2|%s|2captcha (error: %s)\n' "$k" "$b" >> "$TMP" ;;
                     *)                  printf '%s|%s|2captcha\n' "$b" "$k" >> "$TMP" ;;
                   esac
                   sleep 0.35 ;;
    capsolver)     post_balance capsolver     "https://api.capsolver.com/getBalance" "$k"; sleep 0.35 ;;
    anti-captcha)  post_balance anti-captcha  "https://api.anti-captcha.com/getBalance" "$k"; sleep 0.35 ;;
    capmonster)    post_balance capmonster     "https://api.capmonster.cloud/getBalance" "$k"; sleep 0.35 ;;
    uCaptcha)      post_balance uCaptcha      "https://api.ucaptcha.net/getBalance" "$k" ;;
    Solvex)        post_balance Solvex        "https://api.solvex.run/getBalance" "$k" ;;
    NextCaptcha)   post_balance NextCaptcha   "https://api.nextcaptcha.com/getBalance" "$k" ;;
    CaptchaAI)     get_balance  CaptchaAI     "https://ocr.captchaai.com/res.php?key=$k&action=getbalance&json=1" "$k" ;;
    SolveCaptcha)  get_balance  SolveCaptcha  "https://api.solvecaptcha.com/res.php?key=$k&action=getbalance&json=1" "$k" ;;
    *)             : ;;                       # unrecognised name — never silently dropped silently: recorded
  esac
done

# ---- render: funded (desc) then drained / zero / errors ---------------------
sort -t'|' -k1,1gr "$TMP" | awk -F'|' '$1+0>0' | while IFS='|' read -r b k p; do
  printf '%s | $%-10s | %s\n' "$k" "$b" "$p"; done

echo
echo "# habis / kosong / error"
sort -t'|' -k1,1gr "$TMP" | awk -F'|' '$1=="X" || $1=="X2" || $1+0<=0' | while IFS='|' read -r b k p; do
  case "$b" in
    X)  printf '%s | %-10s | %s\n' "$k" "(no body)" "$p" ;;
    X2) printf '%s | %-10s | %s\n' "$k" "(error)"   "$p" ;;
    *)  printf '%s | $%-9s | %s\n' "$k" "$b"        "$p" ;;
  esac
done

echo
awk -F'|' '$1+0>0{s+=$1; n++} END{printf "# total: $%.5f across %d keys (deduped)\n", s, n}' "$TMP"
