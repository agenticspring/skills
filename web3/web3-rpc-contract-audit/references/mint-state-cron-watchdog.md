# Mint-State Cron Watchdog (no_agent, transition-only alerts)

Verified 2026-08-03 on A NONYM (Robinhood Chain 4663). Pattern: a `no_agent=true` cron job runs a bash script every N minutes; the script is SILENT when nothing changed and prints an alert ONLY on state transitions (open / close / sold-out). Works for any state you can read via `cast call` — mint status, floor price, token price, domain DNS.

## Why this shape
- `no_agent=true` cron = zero LLM tokens per tick; scheduler delivers script stdout verbatim.
- Empty stdout → silent tick (watchdog pattern): user gets no spam while mint is closed.
- State files (`/root/.hermes/scripts/*-state.txt`) hold the last-seen state so the alert fires ONCE per transition, not every tick.
- RPC hiccup → `exit 0` silently (retry next tick) — never alert on a transient read failure.

## Script skeleton (`/root/.hermes/scripts/anon-mint-monitor.sh`)

```bash
#!/usr/bin/env bash
set -u
RPC="https://robinhood-rpc.publicnode.com"
NFT="0x...contract..."
CAST="/usr/local/bin/cast"
STATE="/root/.hermes/scripts/anon-mint-state.txt"

active="$( "$CAST" call "$NFT" "mintActive()(bool)" --rpc-url "$RPC" 2>/dev/null | tail -1 )"
minted_raw="$( "$CAST" call "$NFT" "totalMinted()(uint256)" --rpc-url "$RPC" 2>/dev/null | tail -1 )"
[ -z "$active" ] || [ -z "$minted_raw" ] && exit 0   # RPC hiccup → silent

prev="$(cat "$STATE" 2>/dev/null || echo false)"

if [ "$active" = "true" ] && [ "$prev" != "true" ]; then
  echo "true" > "$STATE"
  echo "🚨 MINT OPEN! totalMinted=${minted_raw}/10000 ..."
elif [ "$active" = "false" ] && [ "$prev" = "true" ]; then
  echo "false" > "$STATE"
  echo "🔒 mint closed"
fi
# sold-out: separate state file, one-shot alert when totalMinted >= max
exit 0
```

Key rules:
- `2>/dev/null | tail -1` on every `cast call`; empty = treat as hiccup, not a state change.
- Separate state file per transition (open/close vs sold-out) so they don't clobber each other.
- Always `exit 0` — a nonzero exit makes the scheduler send an error alert.

## Cron job creation (through the `cronjob` tool)
```text
action: create
name:   A NONYM mint monitor
schedule: */10 * * * *
no_agent: true
script:  anon-mint-monitor.sh        # RELATIVE to ~/.hermes/scripts/ (absolute path rejected)
deliver: origin
```
- Script must live at `~/.hermes/scripts/<name>.sh`; pass just the filename.
- After creating, TEST the script once in foreground: while mint is closed it should print nothing and write the state file; re-run → still silent (transition already consumed). Delete the state file to re-arm the open alert.

## Pitfalls
- **First run consumes the transition**: if mint already opened, the very first run writes `true` and prints the alert once — that's correct behavior, but the cron won't re-alert open later (it's a transition detector, not a status reporter). Tell the user the state it found on first run.
- **Do NOT use `?page=N` on Blockscout v2** for anything in the script — `next_page_params` only (see fund-flow-tracing.md §7).
- **cast needs full `--rpc-url`**; omitting it defaults to ETH mainnet.
- Re-arm a transition by `rm`-ing the state file (e.g. after manually checking).
