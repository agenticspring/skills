---
name: onchain-launch-monitor
description: Watch launchpads for new tokens or go-live, alert real-time.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web3, Monitoring, Cron, Telegram, Onchain]
---

# Onchain Launch Monitor

Watches a token-launch platform (website + factory contract + GitHub config repo) and alerts in real time when something changes: the site goes live, a new token CA is created, or the deploy addresses get updated. Built for the pools.trade / Robinhood Chain pattern but generalizes to any launchpad with a public factory contract and a teaser site.

Does NOT verify whether a token is official — that's `token-launch-verify`'s job. This skill is the watcher: detect the change fast, surface the CA, let the other skill classify it.

## When to Use

- "Monitor pools.trade tiap X menit, kabarin kalau live / ada CA baru"
- "Percepat monitoring, tiap 30 detik, kalau ada CA langsung tampilkan"
- Any pre-launch teaser site + factory contract where you want the first-mover alert
- User wants alerts pushed to Telegram without waiting for cron delivery

## Prerequisites

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_HOME_CHANNEL` in `~/.hermes/.env` (required for direct Telegram push)
- Public block explorer API for the chain (Blockscout v2 for Robinhood Chain: `https://robinhoodchain.blockscout.com`)
- Public RPC for `eth_getTransactionByHash` / `eth_getTransactionReceipt`
- Python 3 (stdlib only — urllib, hashlib, re)

## How to Run

Two tiers:

1. **Cron tier (>= 1 minute):** `cronjob` action=create with `no_agent=true`, `script="<monitor>.py"`, schedule `every 10m` / `*/1 * * * *`. The script prints only on change; empty stdout = silent. Delivers to `origin`.
2. **Daemon tier (< 1 minute):** cron rejects `every 30s`. Run a background loop via `terminal` (background=true) that checks every N seconds and calls the Telegram Bot API directly. See `scripts/pools_daemon.py` — copy, adapt the CHECK config, run, don't re-type.

For one-shot checks (not monitoring), just run the script once — it initializes baseline and exits silent, exactly like the first cron tick.

## Quick Reference

```bash
# Baseline + first check (silent on first run, prints if state already known)
python3 ~/.hermes/scripts/pools_monitor.py

# Background daemon (30s loop, direct Telegram push)
cd ~/.hermes/scripts && python3 pools_daemon.py   # via terminal background=true

# Direct Telegram send (no cron delivery dependency)
curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT>&text=<MSG>&disable_web_page_preview=true"
```

## Procedure

1. **Pick the tier.** If the user wants >= 1 min cadence → cron with `no_agent=true`. If faster (30s) → daemon via `terminal` background=true. Cron's minimum is 1 minute; `every 30s` is rejected with `Invalid duration`.
2. **Load env.** Parse `~/.hermes/.env` for `TELEGRAM_BOT_TOKEN` + `TELEGRAM_HOME_CHANNEL` (quote-strip values). Never hardcode the token.
3. **Define the three check sources** (adapt per launchpad):
   - Website: fetch homepage, extract `<title>`, `name="description"`, and a `teaser` flag (e.g. "Coming soon" in HTML). Transition teaser→live is the go-live signal.
   - Config repo: GitHub commits API for the addresses file (`commits?path=...`), plus raw file hash to detect content edits.
   - Factory contract: blockscout `addresses/<FACTORY>/transactions?filter=to` — the newest tx hash is the change cursor. New tx hash = new token created.
4. **Strip CSP nonces before hashing HTML.** `re.sub(r'nonce="[^"]+"', 'NONCE', html)` — nonces are random per request; hashing raw HTML gives a false-positive alert on every fetch.
5. **Report the CA on factory change.** New factory tx → fetch `eth_getTransactionByHash` (calldata, deployer) + `eth_getTransactionReceipt` (logs). The receipt's first log with Transfer topic (`0xddf252ad...`) and zero topic[1] is the mint; the log's `address` is the new CA. Fall back to blockscout `/internal-transactions` `created_contract` when it isn't 500-ing. Verify name/symbol via `eth_call`.
6. **Direct push.** Daemon sends `sendMessage` to `TELEGRAM_HOME_CHANNEL`. Cron tier prints to stdout and lets cron deliver.
7. **Persist state.** JSON state file (`~/.hermes/scripts/<name>_state.json`) holds last-seen hashes and the factory tx cursor. First run stores baseline only — never alert on baseline init.

## Pitfalls

- **Cron rejects sub-minute schedules.** `every 30s` → `Invalid duration`. Daemon is the only way to go faster than 1 minute.
- **Blockscout 500s on fresh txs.** Right after a factory tx, `/transactions/<HASH>` and `/internal-transactions` can 500 or return empty. Use RPC `eth_getTransactionReceipt` — the log address with Transfer-from-zero topic IS the CA.
- **CSP nonces = false-positive alerts.** Every HTTP fetch returns a fresh nonce. Strip them before hashing or the monitor alerts on every tick.
- **Bot tokens flood the factory.** On a permissionless factory, front-run bots deploy tokens within seconds of every new launcher. Expect frequent alerts; add a filter (only alert on website live / GitHub update / non-bot deployer) if it's too noisy.
- **Rate limits.** Public RPC 403s on bursts; blockscout can 422 on short hash prefixes — always pass full hashes. Space requests, retry with backoff.
- **Watch the baseline cursor.** If the state file is deleted, the next run re-baselines silently — you lose the "did anything change since" memory but not the ability to detect future changes.

## Verification

```bash
# After one full loop, state file must exist with a site_hash + factory_tx cursor:
cat ~/.hermes/scripts/pools_monitor_state.json   # {"site_hash": "...", "factory_tx": "0x..."}
# Daemon tier: send a test Telegram message through the same tg_send helper and confirm "ok"
```

If the state file has a factory_tx cursor and a manual `curl` of the factory txs endpoint returns the same hash, the monitor is correctly positioned to detect the next change.
