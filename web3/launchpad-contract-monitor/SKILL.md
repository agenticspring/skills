---
name: launchpad-contract-monitor
description: Watch a launchpad for contract and site changes.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web3, Monitoring, Cron, Launchpad, Recon]
---

# Launchpad Contract Monitor

Silent watchdog for a pre-launch/stealth launchpad (e.g. Uniswap's pools.trade on Robinhood Chain). Polls every N minutes and reports ONLY when something changes: website teaser→live transition, new commits to the SDK addresses file, new launcher/strategy/factory contract entries, or content-hash changes. No change = silence (no spam). Uses a `cronjob` with `no_agent=true` + a stateful script so each tick is a cheap hash compare, not an LLM call.

Does NOT classify tokens as official/sybil — pair with `token-launch-verify` when a new contract appears.

## When to Use

- "Cek tiap 10 menit apakah update contract di pools.trade, kabarin kalau ada update"
- Monitoring any launchpad go-live (teaser site → live app transition)
- Watching a GitHub SDK/addresses file for new contract registrations
- Detecting new launcher/strategy/factory deploys before the official announcement

## Prerequisites

- `python3` with stdlib only (urllib, hashlib, json)
- A `cronjob` delivery target (origin chat works for Telegram/Discord)
- No API keys — all sources are public (site HTML, GitHub API, raw.githubusercontent)

## How to Run

1. Adapt `scripts/launchpad_monitor.py` (state path + URLs for the target launchpad).
2. First run manually via `terminal` — it initializes the baseline JSON and stays silent.
3. Register with `cronjob` action=create, `no_agent=true`, `script=launchpad_monitor.py`, schedule like `every 10m`, `deliver=origin`.

## Quick Reference

```bash
# One-off baseline/check
python3 ~/.hermes/scripts/launchpad_monitor.py
cat ~/.hermes/scripts/launchpad_monitor_state.json   # baseline snapshot

# API endpoints the script hits
https://pools.trade                                        # site HTML
https://api.github.com/repos/Uniswap/sdks/commits?path=sdks/liquidity-launcher-sdk/src/addresses.ts&per_page=1
https://raw.githubusercontent.com/Uniswap/sdks/main/sdks/liquidity-launcher-sdk/src/addresses.ts
```

## Procedure

1. **Write the script** via `write_file` to `~/.hermes/scripts/launchpad_monitor.py`, customizing: `SITE_URL`, `GH_REPO`, `GH_PATH`, `STATE_FILE`.
2. **Baseline it** — run once with `terminal`. Verify `launchpad_monitor_state.json` exists with `site_hash`, `gh_sha`, `raw_hash` populated. If any key is missing, a fetch failed — fix connectivity before scheduling.
3. **Register the cron** with `cronjob`: `no_agent=true` (the script IS the job), `script=launchpad_monitor.py`, `schedule=every 10m`, `deliver=origin`. Note: first baseline run must happen BEFORE scheduling, or the first tick treats baseline-init as a change.
4. **Verify** with `cronjob` action=list — confirm `next_run_at` is set and `state=scheduled`.
5. **On an alert**, run `terminal` + `python3` on the script again to see the current state, then follow up with `token-launch-verify` to classify any new contract.

## Pitfalls

- **First run is baseline, not an alert.** The script must init state silently or the first cron tick spams a false "change".
- **Fetch failures stay silent** (except block). A site or GitHub outage looks like "no change" — that is deliberate for a watchdog, but note it when diagnosing a quiet period.
- **GitHub commits lag on-chain deploys** — a launcher can be deployed hours before the SDK file is updated. Alert on commit SHA AND raw content hash; both matter.
- **No-LLM mode means no reasoning.** The cron delivers raw diff text. If you want interpretation (e.g. "this new launcher is vanity-mined"), use a normal agent cron instead — more expensive, smarter output.
- **Blockscout/API rate limits** apply to follow-up deep-dives; the monitor itself only hits 3 cheap public endpoints per tick.

## Verification

```bash
python3 ~/.hermes/scripts/launchpad_monitor.py && echo "exit 0 = OK (silent)" && test -s ~/.hermes/scripts/launchpad_monitor_state.json && echo "state file populated"
```

A populated state file with `site_hash`, `gh_sha`, `raw_hash` and exit code 0 proves the monitor is live; a second run with no stdout confirms the silent-watchdog contract.

## Support Files

- `scripts/launchpad_monitor.py` — generic watchdog (site HTML hash + GitHub commit SHA + raw file hash); edit the top config block per target.
- `references/pools-trade-case-study.md` — the verified 2026-08-05 pools.trade forensic path: contract table, bot-cluster evidence, website recon findings, and reusable commands. Use as a worked example when monitoring a new launchpad.
